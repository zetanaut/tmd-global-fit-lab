#!/usr/bin/env python3
"""Hash-verify and compare raw gradients from saved endpoint NPZ files only."""
import argparse
from pathlib import Path
import sys
import numpy as np

# Direct execution from a batch script otherwise puts only ``scripts/`` on
# sys.path, not the repository root containing tmdlab.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tmdlab.io import sha, write


def arrays(path):
    with np.load(path, allow_pickle=False) as z:
        if set(z.files) != {"theta", "values", "raw_gradient", "penalized_gradient"}:
            raise ValueError(f"unexpected endpoint inventory: {path}")
        return z["theta"].copy(), z["raw_gradient"].copy()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--cpu", type=Path, required=True)
    p.add_argument("--cpu-sha256", required=True)
    p.add_argument("--a6000", type=Path, required=True)
    p.add_argument("--a6000-sha256", required=True)
    p.add_argument("--threshold", type=float, default=1e-7)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if not (np.isfinite(a.threshold) and a.threshold > 0):
        raise ValueError("finite positive threshold required")
    candidate_theta, candidate_gradient = arrays(a.candidate)
    if not np.isfinite(candidate_theta).all() or not np.isfinite(candidate_gradient).all():
        raise ValueError("candidate theta or gradient invalid")
    comparisons = {}
    for label, path, expected in (("cpu", a.cpu, a.cpu_sha256), ("a6000", a.a6000, a.a6000_sha256)):
        if sha(path) != expected:
            raise ValueError(f"{label} endpoint hash mismatch")
        theta, gradient = arrays(path)
        if not np.isfinite(theta).all() or not np.array_equal(candidate_theta, theta):
            raise ValueError(f"{label} theta differs")
        if gradient.shape != candidate_gradient.shape or not np.isfinite(gradient).all():
            raise ValueError(f"{label} gradient invalid")
        error = float(np.max(np.abs(candidate_gradient - gradient)))
        if error > a.threshold:
            raise ValueError(f"{label} raw-gradient mismatch: {error}")
        comparisons[label] = {"endpoint_sha256": expected, "maximum_absolute_error": error}
    write(a.out, {"schema": "tmd-saved-raw-gradient-comparison-v1",
                  "candidate_endpoint_sha256": sha(a.candidate),
                  "threshold": a.threshold, "passed": True, "comparisons": comparisons})


if __name__ == "__main__":
    main()
