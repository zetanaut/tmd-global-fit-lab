"""Relocatable inventory; the original source manifest is preserved byte-for-byte."""
from pathlib import Path
import numpy as np
from .io import read, sha, digest, within, SOURCE_ID, METRIC_ID

class Bundle:
    def __init__(self, directory, *, verify_all=False):
        self.root = Path(directory).resolve()
        self.index = read(self.root / "bundle.json")
        body = {k:v for k,v in self.index.items() if k != "identity"}
        if self.index.get("identity") != digest(body):
            raise ValueError("bundle identity mismatch")
        if self.index["source_identity"] != SOURCE_ID or self.index["metric_identity"] != METRIC_ID:
            raise ValueError("unrecognized scientific source or metric")
        self.manifest = read(self.file("source-manifest.json"))
        if self.manifest["identity"] != SOURCE_ID or digest({k:v for k,v in self.manifest.items() if k != "identity"}) != SOURCE_ID:
            raise ValueError("original source manifest altered")
        self.rows = self.manifest["rows"]
        if len(self.rows) != 2290 or len(self.index["operators"]) != 2290:
            raise ValueError("exact 2290 rows required")
        self.metric_info = read(self.file("metric.json"))
        if self.metric_info["ids"] != [r["observation_id"] for r in self.rows] or self.metric_info["units"] != [r["unit"] for r in self.rows]:
            raise ValueError("metric/operator row order or units drift")
        if verify_all:
            for name in self.index["files"]:
                self.file(name)

    def file(self, name):
        p = within(self.root, name)
        expected = self.index["files"][name]
        if not p.is_file() or p.stat().st_size != expected["bytes"] or sha(p) != expected["sha256"]:
            raise ValueError(f"artifact hash/size mismatch: {name}")
        return p

    def operator(self, index):
        ref = self.index["operators"][index]
        historical = self.manifest["references"][index]
        m = read(self.file(ref["metadata"]))
        if m["row"] != historical["row"] or m["identity"] != historical["identity"] or self.index["files"][ref["metadata"]]["sha256"] != historical["json_sha256"]:
            raise ValueError("operator row/metadata changed")
        path = self.file(ref["arrays"])
        if self.index["files"][ref["arrays"]]["sha256"] != historical["npz_sha256"]:
            raise ValueError("operator array binding changed")
        with np.load(path, allow_pickle=False) as f:
            arrays = {k:f[k].copy() for k in f.files}
        for k, a in arrays.items():
            spec = m["array_manifest"][k]
            if list(a.shape) != spec["shape"] or str(a.dtype) != spec["dtype"] or not np.isfinite(a).all():
                raise ValueError("operator array schema/finite check failed")
        return m, arrays

    def checkpoint(self, name):
        entry = self.index["checkpoints"][name]
        with np.load(self.file(entry["path"]), allow_pickle=False) as z:
            arrays = {k:z[k].copy() for k in z.files}
        if not all(np.isfinite(v).all() for v in arrays.values()):
            raise ValueError("nonfinite checkpoint")
        return entry, arrays
