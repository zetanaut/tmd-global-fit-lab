#!/usr/bin/env python3
"""One-shot saved-only V7 import. Requires the original local evidence tree.

No model, optimizer, GPU, network, or baseline writes. Exact NPZ bytes are copied;
JSON receipts are explicitly redacted derivatives, never mislabelled originals.
"""
import argparse
from pathlib import Path
import re
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tmdlab.io import read, write, sha, digest, SOURCE_ID, METRIC_ID
from tmdlab.bundle import Bundle
from tmdlab.metric import Metric
from tmdlab.checkpoints import load_overlay

FINAL = {8: "de97942f3a030cbc6648b6b452381d316aa945d1a8629a5360313c80ebd6ae61",
         24: "bfe8a29ab9e2e8ed203f2e5a781038be41aeac76cf52818b00015d9495384ae6"}
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)

def redacted(value, source):
    if isinstance(value, dict):
        return {redacted(k, source): redacted(v, source) for k, v in value.items()
                if k not in {"manager_owner", "manager_route", "command", "reproduce", "latest_handoff_read", "current_addendum"}}
    if isinstance(value, list):
        return [redacted(v, source) for v in value]
    if isinstance(value, str):
        value = value.replace(str(source), "source://study")
        value = re.sub(r"/home/[^\s\"':]+", "[local-path-redacted]", value)
        return UUID.sub("[coordination-id-redacted]", value)
    return value

def main(args):
    root = Path(__file__).resolve().parents[1]
    source = args.source_root.resolve()
    v7 = source / "manager/gpu_film_comparable_continuation_2026_09_12_v7"
    v8 = source / "manager/gpu_film_comparable_continuation_2026_09_12_v8"
    director = source / "2026-09-03/i-x20/outputs"
    bundle = Bundle(args.bundle)
    metric = Metric(bundle)
    evidence_dir = root / "evidence/p0-v7-2026-09-13"
    if evidence_dir.exists() or (root / "checkpoints").exists():
        raise ValueError("immutable import already exists; use a new reviewed import")
    terminal = read(v7 / "terminal_receipt.json")
    if sha(v7 / "terminal_receipt.json") != "8be5ed6162473e3192e52fa3ffaeec1400a750814d293f78ad1cc3f8640643d9":
        raise ValueError("authoritative terminal receipt changed")
    audit_path = director / "GPU_FILM_V7_SAVED_AUDIT_2026-09-13.json"
    audit = read(audit_path)
    # Recheck the immutable scientific pins; do not re-run the original audit harness.
    for path, expected in audit["source_pins"].items():
        if sha(path) != expected:
            raise ValueError("saved audit source pin changed: " + Path(path).name)
    records = {}
    sources = {"terminal": v7 / "terminal_receipt.json", "cleanup": v7 / "cleanup_receipt.json",
               "saved-scientific-audit": audit_path, "v8-cpu-repair": v8 / "gate_repair_disposition.json"}
    for width, start in ((8, "S01"), (24, "S00")):
        cell = v7 / f"attempt_001/film_w{width}_d1_c12_v1/{start}"
        for name in ("parent_verification", "initial_endpoint", "final_endpoint", "summary", "directional_preflight"):
            sources[f"w{width}-{name}"] = cell / (name + ".json")
    for label, path in sources.items():
        derivative = {"schema": "tmd-redacted-evidence-v1", "original_sha256": sha(path),
                      "original_source": redacted(str(path), source),
                      "transformation": "Local paths normalized; coordination identifiers and commands omitted. Scientific numbers retained. Not byte-identical to original.",
                      "content": redacted(read(path), source)}
        target = evidence_dir / (label + ".json")
        write(target, derivative)
        records[label] = {"path": str(target.relative_to(root)), "sha256": sha(target),
                          "original_sha256": sha(path)}
    pins = {redacted(str(path), source): sha(path) for path in (
        director / "DIRECTOR_GLOBAL_FIT_STATUS_2026-09-13.md",
        director / "GPU_FILM_P1_ROUND1_ASSIGNMENT_2026-09-13.md",
        v8 / "continuation_runner.py", v8 / "test_runtime_enforcement.py", v8 / "runtime_gate_test_output.txt")}
    if sha(director / "GPU_FILM_P1_ROUND1_ASSIGNMENT_2026-09-13.md") != "c2ad07eb3dc8a6170d818277b238de00b981e13a09486f9c099105a169ccfb32":
        raise ValueError("assignment changed")
    ids = {}; checks = {}
    for width, start, parent_name, additional in ((8, "S01", "p0-w8-083", 13), (24, "S00", "p0-w24-064", 32)):
        cell = v7 / f"attempt_001/film_w{width}_d1_c12_v1/{start}"
        path = cell / "final.npz"
        if sha(path) != FINAL[width]:
            raise ValueError("wrong exact V7 endpoint")
        parent, _ = bundle.checkpoint(parent_name)
        endpoint = audit["endpoints"][f"film_w{width}_d1_c12_v1/{start}"]
        target = root / "checkpoint-objects" / (FINAL[width] + ".npz")
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(path, target)
        m = {"schema": "tmd-checkpoint-overlay-v1", "label": f"p0-v7-w{width}-{start.lower()}",
             "source_identity": SOURCE_ID, "metric_identity": METRIC_ID,
             "bundle_identity": bundle.index["identity"], "origin_allocation": "p0-remaining32-13-v7",
             "budget_policy": "new_allocation_only", "remaining_origin_updates": 0,
             "accepted_updates": {"screening": 64, "refinement": 96, "total": 160, "new_in_segment": additional},
             "object": {"path": str(target.relative_to(root)), "sha256": FINAL[width], "bytes": target.stat().st_size},
             "parent": {"checkpoint": parent_name, "sha256": endpoint["parent_sha256"], "q_per_measurement": parent["q_per_measurement"]},
             "model": parent["model"], "parameters": parent["parameters"], "parameter_schema": parent["parameter_schema"],
             "q_per_measurement": next(t["endpoint"]["q_per_measurement"] for t in terminal["targets"] if t["architecture"] == f"film_w{width}_d1_c12_v1"),
             "mu": 1e-6, "optimizer_history": "reset_required", "classification": "P0_complete_unconverged",
             "evidence": records["saved-scientific-audit"], "terminal_receipt": records["terminal"],
             "segment_cost": endpoint["budget"], "plateau": endpoint["plateau"]}
        m["identity"] = digest(m)
        write(root / "checkpoints" / (m["identity"] + ".json"), m)
        _, arrays = load_overlay(root, m["identity"], bundle, metric)
        ids[str(width)] = m["identity"]
        checks[str(width)] = metric.describe(arrays["values"])
    w16, arrays16 = bundle.checkpoint("p0-w16-096")
    if sha(bundle.file(w16["path"])) != "cf634461ee7bddae3d76ca90cc03e339bd5b6b272cbb26fb3b5bd7eeb0285843":
        raise ValueError("w16 reference changed")
    checks["16"] = metric.describe(arrays16["values"])
    write(evidence_dir / "index.json", {
        "schema": "tmd-historical-evidence-import-v1", "classification": "P0_complete_unconverged",
        "portable_trial_completion": False, "model_calls": 0, "gpu_calls": 0, "optimizer_calls": 0,
        "verified_scientific_source_pins": len(audit["source_pins"]), "records": records,
        "source_only_hash_pins": pins, "overlays": ids, "saved_array_checks": checks,
        "unchanged_w16": {"checkpoint": "p0-w16-096", "sha256": sha(bundle.file(w16["path"])), "accepted_total": 160},
        "unchanged_baseline": {"bundle_identity": bundle.index["identity"], "bundle_json_sha256": sha(bundle.root / "bundle.json"), "release_lock_sha256": sha(root / "data/baseline-v1.json")},
        "qualifications": ["All endpoints positive and all 188 high-COMPASS rows underpredicted; no architecture winner or convergence.",
            "V6 w24 is an alternative parent branch. V6 w8 repeats the same path, not an independent seed or extra unique accepted updates; retain separate execution cost.",
            "Original terminal cumulative counters are historical reports, not complete project totals: older attempt002 adds 10 forwards and 4 full calls with zero accepted updates.",
            "Missing elapsed time and actual worker peaks remain unknown, not zero; preflight resource_peak is not a worker maximum.",
            "V8 repair: seven CPU surrogate tests, no model/GPU execution or new allowance; Python signal tests do not certify interruption of native CUDA stalls.",
            "Native P1 is separately assigned to Manager and does not wait for portable qualification. No PORT or UVA job was submitted by this import."]})
    print({"overlays": ids, "verified_pins": len(audit["source_pins"]), "evidence": str(evidence_dir.relative_to(root)), "model_calls": 0})

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    main(p.parse_args())
