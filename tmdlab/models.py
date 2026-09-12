"""Portable Nested-FiLM computational port; parameter order matches the baseline.

Transport/import changes are a new implementation, not a relabeling of frozen
source identities. Mandatory checkpoint replay gates certify equivalence before
fitting. No new family or conditioning-placement variant is implied here.
"""
from dataclasses import dataclass, asdict
import math
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

@dataclass(frozen=True)
class Config:
    width: int = 8
    depth: int = 1
    condition_width: int = 12
    flavor_embedding: int = 4
    hadron_embedding: int = 3
    radial_scale: float = 1.0
    initial_width: float = .125
    Qref: float = 3.0

    def validate(self):
        if type(self.width) is not int or type(self.depth) is not int or self.width < 1 or self.depth < 1:
            raise ValueError("positive integer width/depth required")
        fixed = asdict(Config())
        for k, value in asdict(self).items():
            if k not in ("width", "depth") and value != fixed[k]:
                raise ValueError(f"fixed baseline model field changed: {k}")

def radial(b, cfg):
    s = (b/cfg.radial_scale).square()
    u = s/(1+s)
    return u, torch.stack((u, u.square(), u*(1-u), torch.log1p(s)), dim=-1)

class FiLMBlock(nn.Module):
    def __init__(self, width, condition_width):
        super().__init__()
        self.linear1 = nn.Linear(width, width, dtype=torch.float64)
        self.linear2 = nn.Linear(width, width, dtype=torch.float64)
        self.modulation = nn.Linear(condition_width, 2*width, dtype=torch.float64)

    def forward(self, h, c):
        gamma, beta = self.modulation(c).chunk(2, dim=-1)
        v = (1+torch.tanh(gamma))*torch.tanh(self.linear1(h))+torch.tanh(beta)
        return torch.tanh(h+self.linear2(v))

class Boundary(nn.Module):
    def __init__(self, cfg, *, outgoing):
        super().__init__()
        self.cfg, self.is_outgoing = cfg, outgoing
        self.species_count = 30 if outgoing else 10
        self.raw_widths = nn.Parameter(torch.full((self.species_count,), math.log(math.expm1(cfg.initial_width)), dtype=torch.float64))
        self.flavor = nn.Embedding(10, cfg.flavor_embedding, dtype=torch.float64)
        self.hadron = nn.Embedding(3, cfg.hadron_embedding, dtype=torch.float64) if outgoing else None
        nf = 3 + cfg.flavor_embedding + (cfg.hadron_embedding if outgoing else 0)
        self.condition = nn.Sequential(nn.Linear(nf, cfg.condition_width, dtype=torch.float64), nn.Tanh(), nn.Linear(cfg.condition_width, cfg.condition_width, dtype=torch.float64), nn.Tanh())
        self.radial = nn.Linear(4, cfg.width, dtype=torch.float64)
        self.blocks = nn.ModuleList([FiLMBlock(cfg.width, cfg.condition_width) for _ in range(cfg.depth)])
        self.delta_width_head = nn.Linear(cfg.condition_width, 1, dtype=torch.float64)
        self.shape_head = nn.Linear(cfg.width, 1, dtype=torch.float64)
        for head in (self.delta_width_head, self.shape_head):
            nn.init.zeros_(head.weight)
            nn.init.zeros_(head.bias)

    def log_multiplier(self, b, fraction, species):
        if not torch.isfinite(b).all() or (b < 0).any() or not torch.isfinite(fraction).all() or ((fraction <= 0) | (fraction >= 1)).any():
            raise ValueError("invalid boundary coordinates")
        if species.dtype != torch.int64 or ((species < 0) | (species >= self.species_count)).any():
            raise ValueError("invalid mapped species")
        features = [torch.stack((2*fraction-1, torch.log(fraction), torch.log1p(-fraction)), dim=-1), self.flavor(species % 10)]
        if self.is_outgoing:
            features.append(self.hadron(species // 10))
        c = self.condition(torch.cat(features, dim=-1))
        damping = F.softplus(self.raw_widths[species]+self.delta_width_head(c).squeeze(-1))
        u, features_b = radial(b, self.cfg)
        h = torch.tanh(self.radial(features_b))
        for block in self.blocks:
            h = block(h, c)
        result = -damping*b.square()+u*self.shape_head(h).squeeze(-1)
        if not torch.isfinite(result).all() or not (damping > 0).all():
            raise ValueError("nonfinite boundary or zero damping; no clipping")
        return result

class CollinsKernel(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.network = nn.Sequential(nn.Linear(4, cfg.condition_width, dtype=torch.float64), nn.Tanh(), nn.Linear(cfg.condition_width, 1, dtype=torch.float64))
        nn.init.zeros_(self.network[-1].weight)
        nn.init.zeros_(self.network[-1].bias)

    def forward(self, b):
        u, features = radial(b, self.cfg)
        result = u*self.network(features).squeeze(-1)
        if not torch.isfinite(result).all():
            raise ValueError("nonfinite shared CS kernel")
        return result

class Model(nn.Module):
    def __init__(self, cfg=Config()):
        super().__init__()
        cfg.validate()
        self.config, self.Qref = cfg, cfg.Qref
        self.incoming = Boundary(cfg, outgoing=False)
        self.outgoing = Boundary(cfg, outgoing=True)
        self.cs = CollinsKernel(cfg)

def build(cfg=Config(), seed=20260910):
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        return Model(cfg)

def flat(model):
    return np.concatenate([p.detach().cpu().numpy().ravel() for p in model.parameters()]).copy()

def put(model, theta):
    theta = np.asarray(theta, dtype=np.float64)
    if theta.shape != (sum(p.numel() for p in model.parameters()),) or not np.isfinite(theta).all():
        raise ValueError("finite exact parameter vector required")
    i = 0
    with torch.no_grad():
        for p in model.parameters():
            p.copy_(torch.as_tensor(theta[i:i+p.numel()].reshape(p.shape), device=p.device))
            i += p.numel()

def schema(model):
    return [{"name": n, "shape": list(p.shape), "dtype": str(p.dtype)} for n,p in model.named_parameters()]

