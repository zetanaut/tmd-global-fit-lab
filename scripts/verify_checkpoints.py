#!/usr/bin/env python3
"""Repeatable saved-array overlay check, without model/GPU/optimizer calls."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tmdlab.bundle import Bundle
from tmdlab.checkpoints import load_overlay
from tmdlab.io import read, sha
from tmdlab.metric import Metric

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", type=Path, required=True)
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    bundle = Bundle(args.bundle); metric = Metric(bundle)
    index = read(root / "evidence/p0-v7-2026-09-13/index.json")
    baseline = index["unchanged_baseline"]
    if (sha(root / "data/baseline-v1.json") != baseline["release_lock_sha256"] or
        sha(bundle.root / "bundle.json") != baseline["bundle_json_sha256"]):
        raise ValueError("baseline lock/inventory changed")
    for width, identity in index["overlays"].items():
        m, a = load_overlay(root, identity, bundle, metric)
        d = metric.describe(a["values"])
        print(f"w{width}: sha256={m['object']['sha256']} q/N={d['q_per_measurement']:.15f}; positive=2290; high-COMPASS underpredicted={d['high_COMPASS']['underpredicted']}/188")
    ref = index["unchanged_w16"]
    entry, a = bundle.checkpoint(ref["checkpoint"])
    if sha(bundle.file(entry["path"])) != ref["sha256"]:
        raise ValueError("w16 reference changed")
    print(f"w16 reference unchanged: q/N={metric.describe(a['values'])['q_per_measurement']:.15f}")
    print("saved-only verification passed; model=0 optimizer=0 GPU=0; no baseline writes")
