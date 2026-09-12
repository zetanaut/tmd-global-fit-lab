"""Portable signed grouped contraction; CPU/GPU share identical float64 algebra.

New transport/evaluator implementation. Replay and directional gates are
mandatory; its implementation identity is never the historical engine identity.
"""
import time
import numpy as np
import torch
from .io import read, digest
from .models import put

KEYS = ("coordinates", "point_index", "species1", "species2")

class Engine:
    def __init__(self, model, bundle, device, *, indices=None, cache_gib=12, deadline=None):
        self.device = torch.device(device)
        if self.device.type not in ("cpu", "cuda") or self.device.type == "cuda" and not torch.cuda.is_available():
            raise ValueError("explicit available CPU/CUDA backend required")
        self.model = model.to(self.device)
        self.indices = list(range(2290)) if indices is None else list(indices)
        if not self.indices or len(set(self.indices)) != len(self.indices) or any(type(i) is not int or not 0 <= i < 2290 for i in self.indices):
            raise ValueError("unique exact row indices required")
        groups = {}
        for index in self.indices:
            m = read(bundle.file(bundle.index["operators"][index]["metadata"]))
            key = digest(dict(process=m["row"]["process"], arrays={k:m["array_manifest"][k] for k in KEYS}))
            groups.setdefault(key, []).append(index)
        self.groups, self.cache_bytes = [], 0
        self.signatures = {}
        for indices_in_group in groups.values():
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError("preparation deadline")
            weights, metas, representative = [], [], None
            for i in indices_in_group:
                m, a = bundle.operator(i)
                if representative is None:
                    representative = a
                elif not all(np.array_equal(a[k], representative[k]) for k in KEYS):
                    raise ValueError("group metadata/actual array mismatch")
                weights.append(a["weights"])
                metas.append(m)
                for key in ("metadata", "arrays"):
                    p = bundle.root / bundle.index["operators"][i][key]
                    self.signatures[p] = (p.stat().st_size, p.stat().st_mtime_ns)
            a = representative
            ix, c = a["point_index"], a["coordinates"]
            process = metas[0]["row"]["process"]
            n2 = 30 if process == "SIDIS" else 10
            k1, i1 = np.unique(ix*10+a["species1"], return_inverse=True)
            k2, i2 = np.unique(ix*n2+a["species2"], return_inverse=True)
            points, ip = np.unique(ix, return_inverse=True)
            numeric = dict(c1=c[k1//10,:2], c2=c[k2//n2][:,[0,2]], cp=c[points][:,[0,3]], s1=k1%10, s2=k2%n2, i1=i1, i2=i2, ip=ip, weights=np.stack(weights), fixed=np.array([m["fixed_numerator"] for m in metas]), denominator=np.array([m["denominator"] for m in metas]), volume=np.array([m["density_volume"] for m in metas]))
            size = sum(a.size*8 for a in numeric.values())
            if self.cache_bytes+size > cache_gib*2**30:
                raise MemoryError("declared cache ceiling before allocation")
            numeric = {k:torch.tensor(v, device=self.device, dtype=torch.int64 if k in ("s1","s2","i1","i2","ip") else torch.float64) for k,v in numeric.items()}
            if not (numeric["denominator"] > 0).all() or not (numeric["volume"] > 0).all():
                raise ValueError("invalid operator normalization")
            self.groups.append(dict(numeric, indices=indices_in_group, process=process))
            self.cache_bytes += size

    def evaluate(self, theta, cotangent=None, *, deadline=None):
        for p,sig in self.signatures.items():
            if (p.stat().st_size, p.stat().st_mtime_ns) != sig:
                raise ValueError("cached source file changed")
        put(self.model, theta)
        positions = {v:i for i,v in enumerate(self.indices)}
        params = tuple(self.model.parameters())
        nparams = sum(p.numel() for p in params)
        values = torch.empty(len(self.indices), dtype=torch.float64, device=self.device)
        gradient = torch.zeros(nparams, dtype=torch.float64, device=self.device) if cotangent is not None else None
        if cotangent is not None:
            cotangent = np.asarray(cotangent)
            if cotangent.shape != (len(self.indices),) or not np.isfinite(cotangent).all():
                raise ValueError("invalid cotangent")
            cotangent = torch.tensor(cotangent, device=self.device, dtype=torch.float64)
        for g in self.groups:
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError("evaluator deadline")
            dest = [positions[i] for i in g["indices"]]
            with torch.set_grad_enabled(cotangent is not None):
                right = self.model.outgoing if g["process"] == "SIDIS" else self.model.incoming
                left = self.model.incoming.log_multiplier(g["c1"][:,0],g["c1"][:,1],g["s1"])
                other = right.log_multiplier(g["c2"][:,0],g["c2"][:,1],g["s2"])
                kernel = self.model.cs(g["cp"][:,0])
                logs = left[g["i1"]]+other[g["i2"]]+(2*kernel*torch.log(g["cp"][:,1]/self.model.Qref))[g["ip"]]
                p = torch.exp(logs)
                if not torch.isfinite(logs).all() or not torch.isfinite(p).all():
                    raise ValueError("nonfinite products; no clipping")
                with torch.no_grad():
                    values[dest] = ((g["weights"]@p.detach())+g["fixed"])/g["denominator"]/g["volume"]
                if cotangent is not None:
                    effective = g["weights"].T@(cotangent[dest]/g["denominator"]/g["volume"])
                    grads = torch.autograd.grad(torch.dot(effective,p), params, allow_unused=True)
                    offset = 0
                    for parameter, grad in zip(params,grads):
                        if grad is not None:
                            gradient[offset:offset+parameter.numel()].add_(grad.detach().ravel())
                        offset += parameter.numel()
        if not torch.isfinite(values).all() or gradient is not None and not torch.isfinite(gradient).all():
            raise ValueError("nonfinite observable/VJP")
        return values.cpu().numpy().copy(), None if gradient is None else gradient.cpu().numpy().copy()

    def close(self):
        self.groups.clear()
        self.model = None
        if self.device.type == "cuda":
            torch.cuda.empty_cache()
