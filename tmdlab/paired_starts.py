"""Deterministic paired width-start candidates; never a scientific trial route.

Each seed first creates a distinct *narrow* parameter vector.  Wider models are
then function-preserving embeddings of that same vector.  This ordering is
important: varying only a widening seed would produce cosmetically different
wide models from one narrow start, not independent paired starts.

This module deliberately makes no operator, metric, feasibility, repair or
optimizer call.  Candidates must pass a separately budgeted all-observable
feasibility/replay gate and be registered as immutable starts before use.
"""
import hashlib
import math
from dataclasses import asdict
import numpy as np
import torch

from .initialization import widen
from .models import build, flat, put


def _candidate_digest(theta):
    theta = np.ascontiguousarray(theta, dtype=np.float64)
    return hashlib.sha256(theta.tobytes()).hexdigest()


def _validate_source(source):
    cfg = source.config
    cfg.validate()
    if any(p.device.type != "cpu" or p.dtype != torch.float64 for p in source.parameters()):
        raise ValueError("paired starts require a CPU float64 source")
    theta = flat(source)
    if not np.isfinite(theta).all():
        raise ValueError("paired starts require finite source parameters")
    return cfg, theta


def perturb_narrow(source, *, seed, radius):
    """Return a deterministic, bounded distinct narrow candidate and receipt.

    ``radius`` is the Euclidean norm of the parameter-space perturbation. It is
    deliberately small and explicit; it is not a feasibility claim or a model
    evaluation. A scientific start protocol must record the later all-row cost.
    """
    if type(seed) is not int:
        raise ValueError("integer paired-start seed required")
    if type(radius) not in (int, float) or not math.isfinite(radius) or not 0 < radius <= .1:
        raise ValueError("paired-start radius must be finite and in (0,.1]")
    cfg, theta = _validate_source(source)
    rng = np.random.default_rng(seed)
    direction = rng.normal(size=theta.size)
    norm = float(np.linalg.norm(direction))
    if not math.isfinite(norm) or norm == 0:
        raise ValueError("failed to construct paired-start direction")
    candidate_theta = theta + float(radius) * direction / norm
    realized = float(np.linalg.norm(candidate_theta-theta))
    # A positive requested radius can vanish when it is below the ULP of a
    # large saved parameter. Conversely, rounding can materially exceed it.
    # Neither outcome is a distinct, bounded paired start.
    tolerance = max(1e-15, float(radius)*1e-10)
    if not math.isfinite(realized) or realized == 0 or abs(realized-float(radius)) > tolerance:
        raise ValueError("paired-start radius is not representable at this source scale")
    candidate = build(cfg, seed=seed)
    put(candidate, candidate_theta)
    receipt = dict(schema="tmd-paired-width-narrow-candidate-v1",
        seed=seed, radius=float(radius), source_model=asdict(cfg),
        source_parameter_sha256=_candidate_digest(theta),
        candidate_parameter_sha256=_candidate_digest(candidate_theta),
        parameter_count=int(theta.size), perturbation_l2=realized,
        model_calls=0, feasibility_verified=False,
        full_observable_replay_required=True,
        note="Candidate only; bounded feasibility/repair and registered-start gates remain required.")
    return candidate, receipt


def paired_width_candidates(source, *, seeds, target_widths, radius, widening_seed=20260913):
    """Build common-narrow candidates and their exact wider partners.

    The return value intentionally contains in-memory models rather than a
    checkpoint format, so this function cannot silently create a runnable start
    or consume a scientific allowance.
    """
    if type(widening_seed) is not int:
        raise ValueError("integer widening seed required")
    cfg, _ = _validate_source(source)
    if not isinstance(seeds, (tuple, list)) or len(seeds) < 2 or any(type(s) is not int for s in seeds) or len(set(seeds)) != len(seeds):
        raise ValueError("at least two distinct integer narrow seeds required")
    widths = tuple(target_widths)
    if (not widths or any(type(w) is not int or w <= cfg.width for w in widths)
        or len(set(widths)) != len(widths)):
        raise ValueError("distinct wider widths required")
    result = {}
    for narrow_seed in seeds:
        narrow, receipt = perturb_narrow(source, seed=narrow_seed, radius=radius)
        partners = {}
        for width in widths:
            # This controls only new hidden features after the common narrow
            # candidate is fixed. It never substitutes for ``narrow_seed``.
            partner, proof = widen(narrow, width, seed=widening_seed + 1009*narrow_seed + width)
            partners[width] = dict(model=partner, transport=proof)
        result[narrow_seed] = dict(narrow=narrow, receipt=receipt, partners=partners)
    digests = [entry["receipt"]["candidate_parameter_sha256"] for entry in result.values()]
    if len(set(digests)) != len(digests):
        raise ValueError("paired narrow candidates unexpectedly collide")
    return dict(schema="tmd-paired-width-candidate-set-v1", source_model=asdict(cfg),
        narrow_seeds=list(seeds), target_widths=list(widths), radius=float(radius),
        candidates=result, model_calls=0, feasibility_verified=False,
        full_observable_replay_required=True,
        note="No candidate is a registered checkpoint or ready trial.")
