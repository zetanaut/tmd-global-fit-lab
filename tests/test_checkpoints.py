"""Saved-artifact and pure-contract tests. No model or optimizer construction."""
import copy
from pathlib import Path
import shutil
from types import SimpleNamespace
import numpy as np
import pytest
from tmdlab.io import read, write, digest
from tmdlab.checkpoints import manifest, validate_manifest, validate_binding, load_overlay

ROOT = Path(__file__).resolve().parents[1]
INDEX = read(ROOT / "evidence/p0-v7-2026-09-13/index.json")

def spec(m):
    return {"start_checkpoint": "overlay:" + m["identity"], "kind": "continuation", "phase": "P1",
            "bundle_identity": m["bundle_identity"], "model": m["model"],
            "checkpoint_binding": {"endpoint_sha256": m["object"]["sha256"], "parent_sha256": m["parent"]["sha256"],
                "accepted_updates_before": 160, "optimizer_history_reset": True,
                "allocation_id": "p1-example-not-authorized", "budget_origin": "new_allocation"}}

@pytest.mark.parametrize("width", ["8", "24"])
def test_exact_registry_objects_and_binding(width):
    m = manifest(ROOT, INDEX["overlays"][width])
    validate_binding(spec(m), m)
    with np.load(ROOT / m["object"]["path"], allow_pickle=False) as z:
        assert z["theta"].shape == (m["parameters"],)
        assert z["values"].shape == (2290,)
        assert (z["values"] > 0).all()
        assert abs(float(z["q_per_measurement"]) - m["q_per_measurement"]) < 1e-12

@pytest.mark.parametrize("field,value", [("endpoint_sha256", "0"*64), ("parent_sha256", "0"*64),
    ("accepted_updates_before", 147), ("optimizer_history_reset", False),
    ("allocation_id", "p0-remaining32-13-v7"), ("budget_origin", "remaining_p0")])
def test_wrong_parent_and_stale_budget_rejected(field, value):
    m = manifest(ROOT, INDEX["overlays"]["8"]); t = spec(m)
    t["checkpoint_binding"][field] = value
    with pytest.raises(ValueError): validate_binding(t, m)

@pytest.mark.parametrize("field,value", [("phase", "P0"), ("phase", "p0"), ("phase", ""),
    ("bundle_identity", "0"*64), ("model", {"width": 24, "depth": 1})])
def test_wrong_trial_identity_rejected(field, value):
    m = manifest(ROOT, INDEX["overlays"]["8"]); t = spec(m); t[field] = value
    with pytest.raises(ValueError): validate_binding(t, m)

def test_tamper_identity_and_path_escape():
    m = copy.deepcopy(manifest(ROOT, INDEX["overlays"]["8"]))
    m["q_per_measurement"] += 1
    with pytest.raises(ValueError): validate_manifest(m)
    m["object"]["path"] = "../outside.npz"
    m["identity"] = digest({k:v for k,v in m.items() if k != "identity"})
    with pytest.raises(ValueError): validate_manifest(m)
    with pytest.raises(ValueError): manifest(ROOT, "../outside")

def fake_bundle(m, tmp_path):
    # Original parent bytes are not needed in unit tests; hash check is separately
    # exercised using the real immutable bundle by the saved-only import verifier.
    parent = {k: m[k] for k in ("model", "parameter_schema", "parameters")}
    parent.update(path="parent.npz", q_per_measurement=m["parent"]["q_per_measurement"])
    return SimpleNamespace(index={"identity": m["bundle_identity"]},
                           checkpoint=lambda name: (parent, {}), file=lambda name: tmp_path / name)

@pytest.mark.parametrize("fault", ["object", "schema", "parent", "evidence", "q", "nonpositive", "ledger"])
def test_loader_fails_closed_before_model(tmp_path, monkeypatch, fault):
    from tmdlab import checkpoints
    from tmdlab.io import sha as real_sha
    m = copy.deepcopy(manifest(ROOT, INDEX["overlays"]["8"]))
    for directory in ("checkpoints", "checkpoint-objects", "evidence"):
        shutil.copytree(ROOT / directory, tmp_path / directory)
    bundle = fake_bundle(m, tmp_path)
    def hashed(path):
        return m["parent"]["sha256"] if Path(path).name == "parent.npz" else real_sha(path)
    monkeypatch.setattr(checkpoints, "sha", hashed)
    metric = SimpleNamespace(score=lambda values, mu: {"q_per_measurement": m["q_per_measurement"], "barrier": 0., "objective": 0.})
    if fault == "object":
        (tmp_path / m["object"]["path"]).write_bytes(b"tampered")
    elif fault == "schema":
        parent, _ = bundle.checkpoint("unused")
        parent["model"] = {"width": 24}
        bundle.checkpoint=lambda name: (parent, {})
    elif fault == "parent":
        monkeypatch.setattr(checkpoints, "sha", lambda path: "0"*64 if Path(path).name == "parent.npz" else real_sha(path))
    elif fault == "evidence":
        (tmp_path / m["evidence"]["path"]).write_text("{}")
    elif fault == "q":
        metric.score=lambda values, mu: {"q_per_measurement": m["q_per_measurement"] + 1}
    elif fault == "nonpositive":
        metric.score=lambda values, mu: None
    else:
        m["accepted_updates"]["total"] += 1; m["accepted_updates"]["refinement"] += 1
        m["identity"] = digest({k:v for k,v in m.items() if k != "identity"})
        write(tmp_path / "checkpoints" / (m["identity"] + ".json"), m)
    with pytest.raises(ValueError): load_overlay(tmp_path, m["identity"], bundle, metric)

def test_no_private_coordination_data_in_import():
    import re
    for path in (ROOT / "evidence").glob("*/*.json"):
        text = path.read_text()
        assert "/home/" not in text
        assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", text)
        assert "github_pat_" not in text
