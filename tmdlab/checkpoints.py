"""Content-addressed saved endpoints; no model construction or optimizer calls.

The immutable operator bundle stays untouched. Small endpoint objects live in
the code checkout; the trial pins the canonical manifest identity, not an alias.
"""
import math
from pathlib import Path
import re
import numpy as np
from .io import read, sha, digest, within, SOURCE_ID, METRIC_ID

def validate_manifest(m):
    body = {k: v for k, v in m.items() if k != "identity"}
    if m.get("schema") != "tmd-checkpoint-overlay-v1" or m.get("identity") != digest(body):
        raise ValueError("checkpoint manifest identity mismatch")
    if m["source_identity"] != SOURCE_ID or m["metric_identity"] != METRIC_ID:
        raise ValueError("checkpoint scientific identity mismatch")
    for value in (m["bundle_identity"], m["object"]["sha256"], m["parent"]["sha256"], m["evidence"]["sha256"]):
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("exact checkpoint/source hash required")
    if m["object"]["path"] != "checkpoint-objects/" + m["object"]["sha256"] + ".npz":
        raise ValueError("content-addressed object path required")
    if type(m["object"]["bytes"]) is not int or not 0 < m["object"]["bytes"] <= 8 * 1024**2:
        raise ValueError("small checkpoint object size required")
    if not math.isfinite(m["q_per_measurement"]) or m["q_per_measurement"] < 0:
        raise ValueError("invalid saved q")
    if m["optimizer_history"] != "reset_required" or m["budget_policy"] != "new_allocation_only":
        raise ValueError("history reset and fresh allocation required")
    n = m["accepted_updates"]
    if any(type(n[k]) is not int or n[k] < 0 for k in ("screening", "refinement", "total", "new_in_segment")):
        raise ValueError("invalid accepted-update ledger")
    if n["screening"] + n["refinement"] != n["total"] or n["new_in_segment"] > n["refinement"]:
        raise ValueError("inconsistent accepted-update ledger")
    if m["remaining_origin_updates"] != 0:
        raise ValueError("closed allocation must have zero remaining updates")
    return m

def manifest(root, identity):
    if not re.fullmatch(r"[0-9a-f]{64}", identity):
        raise ValueError("invalid overlay identity")
    m = validate_manifest(read(within(root, "checkpoints/" + identity + ".json")))
    if m["identity"] != identity:
        raise ValueError("checkpoint filename identity mismatch")
    return m

def validate_binding(trial, m):
    """A starting endpoint is not a grant to replay its already spent budget."""
    if trial["start_checkpoint"] != "overlay:" + m["identity"]:
        raise ValueError("wrong starting endpoint")
    b = trial.get("checkpoint_binding", {})
    expected = {"endpoint_sha256": m["object"]["sha256"],
                "parent_sha256": m["parent"]["sha256"],
                "accepted_updates_before": m["accepted_updates"]["total"],
                "optimizer_history_reset": True}
    if any(b.get(k) != v for k, v in expected.items()) or b.get("optimizer_history_reset") is not True:
        raise ValueError("wrong parent, endpoint, history or spent-budget binding")
    if trial["bundle_identity"] != m["bundle_identity"] or trial["model"] != m["model"]:
        raise ValueError("checkpoint trial bundle/model mismatch")
    if trial["kind"] == "continuation":
        allocation = b.get("allocation_id", "")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,95}", allocation) or allocation == m["origin_allocation"]:
            raise ValueError("new preregistered allocation required; origin budget consumed")
        if b.get("budget_origin") != "new_allocation" or not trial.get("phase") or trial["phase"].upper() == "P0":
            raise ValueError("cannot reuse consumed P0 budget")

def load_overlay(root, identity, bundle, metric, *, trial=None):
    m = manifest(root, identity)
    if m["bundle_identity"] != bundle.index["identity"]:
        raise ValueError("overlay/bundle mismatch")
    # Schema is inherited from the exact original parent, not guessed from width.
    parent, _ = bundle.checkpoint(m["parent"]["checkpoint"])
    if sha(bundle.file(parent["path"])) != m["parent"]["sha256"]:
        raise ValueError("wrong historical parent")
    for key in ("model", "parameter_schema", "parameters"):
        if m[key] != parent[key]:
            raise ValueError("parent parameter schema/model mismatch")
    if abs(parent["q_per_measurement"] - m["parent"]["q_per_measurement"]) > 1e-12:
        raise ValueError("parent q mismatch")
    evidence = within(root, m["evidence"]["path"])
    if sha(evidence) != m["evidence"]["sha256"]:
        raise ValueError("checkpoint evidence hash mismatch")
    recorded = read(evidence)["content"]
    matches = [e for e in recorded["endpoints"].values() if e["sha256"] == m["object"]["sha256"]]
    if len(matches) != 1:
        raise ValueError("endpoint not uniquely bound to scientific evidence")
    e = matches[0]
    if (e.get("parent_sha256") != m["parent"]["sha256"] or
        e["total_accepted"] != m["accepted_updates"]["total"] or
        e["new_accepted"] != m["accepted_updates"]["new_in_segment"] or
        abs(e["endpoint"]["q_per_measurement"] - m["q_per_measurement"]) > 1e-12 or
        e["mu"] != m["mu"] or e["budget"] != m["segment_cost"] or
        e["plateau"] != m["plateau"] or not e["parent_replay_exact"] or not e["terminal_checkpoint_exact"]):
        raise ValueError("scientific evidence/lineage/ledger mismatch")
    obj = m["object"]; path = within(root, obj["path"])
    if path.stat().st_size != obj["bytes"] or sha(path) != obj["sha256"]:
        raise ValueError("checkpoint object hash/size mismatch")
    with np.load(path, allow_pickle=False) as z:
        arrays = {k: z[k].copy() for k in z.files}
    shapes = {"theta": (m["parameters"],), "values": (2290,),
              "penalized_gradient": (m["parameters"],), "raw_gradient": (m["parameters"],),
              "q_per_measurement": (), "barrier": (), "objective": ()}
    if set(arrays) != set(shapes):
        raise ValueError("checkpoint array inventory mismatch")
    for key, value in arrays.items():
        if value.shape != shapes[key] or value.dtype != np.dtype("float64") or not np.isfinite(value).all():
            raise ValueError("checkpoint array schema/finite mismatch")
    score = metric.score(arrays["values"], m["mu"])
    if score is None or abs(score["q_per_measurement"] - m["q_per_measurement"]) > 1e-8:
        raise ValueError("saved-array positivity/q replay failed")
    if abs(float(arrays["q_per_measurement"]) - m["q_per_measurement"]) > 1e-12:
        raise ValueError("embedded q mismatch")
    for key in ("barrier", "objective"):
        if abs(float(arrays[key]) - score[key]) > 1e-10:
            raise ValueError("embedded saved objective/barrier mismatch")
    if trial is not None:
        validate_binding(trial, m)
    return m, arrays
