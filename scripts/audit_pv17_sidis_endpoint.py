#!/usr/bin/env python3
"""Replay a bound trained endpoint on the complete PV17 SIDIS operators.

This is a feasibility audit, not a PV17 fit.  It applies an endpoint trained on
the existing 2,290-observation likelihood to the separately constructed PV17
SIDIS point operators and reports only aggregate values and row identifiers.
Third-party measurements and the local row manifest remain outside git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
import sys
from typing import Any

import numpy as np
import torch

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tmdlab.models import Config, build, put
from tmdlab.pv17 import evaluate_sidis_point_arrays


EXPECTED_ROWS = 7_990
EXPECTED_ENDPOINT_NONPOSITIVE = 16


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def numeric_summary(values: np.ndarray) -> dict[str, Any]:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
        raise ValueError("finite nonempty one-dimensional predictions required")
    return {
        "rows": int(len(values)),
        "minimum": float(values.min()),
        "maximum": float(values.max()),
        "nonpositive": int(np.count_nonzero(values <= 0)),
    }


def grouped_summaries(records: list[dict[str, Any]], values: np.ndarray, key: str):
    labels = sorted({record[key] for record in records})
    return {
        label: numeric_summary(
            np.asarray(
                [value for record, value in zip(records, values) if record[key] == label],
                dtype=np.float64,
            )
        )
        for label in labels
    }


def nonpositive_rows(
    records: list[dict[str, Any]], values: np.ndarray
) -> list[dict[str, Any]]:
    rows = []
    for record, value in zip(records, values):
        if value <= 0:
            weight = float(record["transition_weight"])
            role = "FO_only" if weight == 0 else "full_additive" if weight == 1 else "transition"
            rows.append(
                {
                    "selected_index": int(record["selected_index"]),
                    "experiment": record["experiment"],
                    "target": record["target"],
                    "hadron": record["detected_hadron"],
                    "matching_role": role,
                    "qT_over_Q": float(record["qT_over_Q"]),
                    "prediction": float(value),
                }
            )
    return rows


def shard_receipt_identity_valid(receipt: dict[str, Any]) -> bool:
    body = {key: value for key, value in receipt.items() if key != "identity"}
    body["diagnostics"] = dict(body["diagnostics"])
    body["diagnostics"].pop("wall_seconds_informational", None)
    return receipt.get("identity") == hashlib.sha256(
        canonical_json(body).encode("utf-8")
    ).hexdigest()


def load_campaign(campaign_dir: Path, plan_identity: str):
    records: list[dict[str, Any]] = []
    arrays: list[dict[str, np.ndarray]] = []
    identities = []
    for receipt_path in sorted(campaign_dir.glob("shard-*.json")):
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if not shard_receipt_identity_valid(receipt):
            raise ValueError(f"shard receipt identity mismatch: {receipt_path}")
        if receipt.get("campaign_plan_identity") != plan_identity:
            raise ValueError(f"shard campaign-plan mismatch: {receipt_path}")
        arrays_path = receipt_path.with_suffix(".npz")
        if sha256_file(arrays_path) != receipt["arrays"]["npz_sha256"]:
            raise ValueError(f"shard array hash mismatch: {arrays_path}")
        with np.load(arrays_path, allow_pickle=False) as archive:
            item = {name: archive[name].copy() for name in archive.files}
        if len(receipt["records"]) != len(item["fixed_predictions"]):
            raise ValueError(f"shard row count mismatch: {receipt_path}")
        records.extend(receipt["records"])
        arrays.append(item)
        identities.append(receipt["identity"])
    if not arrays:
        raise ValueError("no completed SIDIS shards found")
    return records, arrays, identities


def audit(
    campaign_dir: Path,
    campaign_receipt_path: Path,
    endpoint_path: Path,
    result_path: Path,
    *,
    require_full_population: bool = True,
) -> dict[str, Any]:
    campaign = json.loads(campaign_receipt_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    endpoint_sha = sha256_file(endpoint_path)
    expected_sha = result["files"]["last.npz"]["sha256"]
    if endpoint_sha != expected_sha or endpoint_sha != result["audit"]["endpoint_sha256"]:
        raise ValueError("endpoint does not match the immutable result receipt")
    if result["model"] != {"depth": 1, "width": 8}:
        raise ValueError("this audit requires the registered width-8 depth-1 endpoint")

    records, shards, shard_identities = load_campaign(
        campaign_dir, campaign["campaign_plan_identity"]
    )
    identities_digest = hashlib.sha256(
        canonical_json(shard_identities).encode("utf-8")
    ).hexdigest()
    if identities_digest != campaign["shard_binding"]["identities_ordered_sha256"]:
        raise ValueError("shards do not match the public campaign receipt")
    if require_full_population and (
        len(records) != EXPECTED_ROWS
        or campaign["counts"]["selected_SIDIS_raw_rows"] != EXPECTED_ROWS
    ):
        raise ValueError("complete 7,990-row PV17 SIDIS campaign required")

    with np.load(endpoint_path, allow_pickle=False) as archive:
        theta = archive["theta"].copy()
    model = build(Config(width=8, depth=1))
    put(model, theta)
    model.eval()

    endpoint_values = []
    controls = []
    fixed = []
    with torch.no_grad():
        for arrays in shards:
            endpoint_values.append(
                evaluate_sidis_point_arrays(model, arrays).detach().cpu().numpy()
            )
            controls.append(arrays["Gaussian_controls"])
            fixed.append(arrays["fixed_predictions"])
    endpoint_values = np.concatenate(endpoint_values)
    controls = np.concatenate(controls)
    fixed = np.concatenate(fixed)

    endpoint_bad = nonpositive_rows(records, endpoint_values)
    control_bad = nonpositive_rows(records, controls)
    endpoint_bad_ids = {row["selected_index"] for row in endpoint_bad}
    control_bad_ids = {row["selected_index"] for row in control_bad}
    invariants = {
        "exact_7990_raw_rows": len(records) == EXPECTED_ROWS,
        "all_endpoint_predictions_finite": bool(np.isfinite(endpoint_values).all()),
        "endpoint_is_bound_to_public_result": endpoint_sha == expected_sha,
        "all_nonpositive_endpoint_rows_are_HERMES_Kminus": all(
            row["experiment"] == "HERMES" and row["hadron"] == "kminus"
            for row in endpoint_bad
        ),
        "observed_16_nonpositive_endpoint_rows": len(endpoint_bad) == EXPECTED_ENDPOINT_NONPOSITIVE,
        "complete_COMPASS_raw_positivity": all(
            value > 0
            for record, value in zip(records, endpoint_values)
            if record["experiment"] == "COMPASS"
        ),
    }
    receipt = {
        "schema": "pv17-current-regional-sidis-endpoint-feasibility-v1",
        "status": "blocked_nonpositive_HERMES_Kminus_predictions",
        "campaign": {
            "receipt": str(campaign_receipt_path),
            "identity": campaign["identity"],
            "plan_identity": campaign["campaign_plan_identity"],
            "shards": len(shards),
        },
        "transferred_endpoint": {
            "trained_likelihood_observations": 2_290,
            "is_a_PV17_fit": False,
            "trial_id": result["trial_id"],
            "result_identity": result["identity"],
            "result_receipt_sha256": sha256_file(result_path),
            "endpoint_sha256": endpoint_sha,
            "theta_bytes_sha256": hashlib.sha256(
                np.ascontiguousarray(theta, dtype=np.float64).tobytes()
            ).hexdigest(),
            "width": result["model"]["width"],
            "depth": result["model"]["depth"],
            "trajectory_accepted_updates": result["trajectory_counters"]["accepted_updates"],
            "source_likelihood_q_per_measurement": result["audit"]["q_per_measurement"],
        },
        "predictions": {
            "endpoint": numeric_summary(endpoint_values),
            "Gaussian_control": numeric_summary(controls),
            "fixed_contribution": numeric_summary(fixed),
            "endpoint_by_experiment": grouped_summaries(records, endpoint_values, "experiment"),
            "endpoint_by_hadron": grouped_summaries(records, endpoint_values, "detected_hadron"),
            "endpoint_by_target": grouped_summaries(records, endpoint_values, "target"),
        },
        "nonpositive": {
            "endpoint_rows": endpoint_bad,
            "Gaussian_control_selected_indices": sorted(control_bad_ids),
            "endpoint_selected_indices": sorted(endpoint_bad_ids),
            "overlap": len(control_bad_ids & endpoint_bad_ids),
            "recovered_from_Gaussian_control": sorted(control_bad_ids - endpoint_bad_ids),
            "new_relative_to_Gaussian_control": sorted(endpoint_bad_ids - control_bad_ids),
        },
        "matching_role_counts": dict(
            sorted(Counter(row["matching_role"] for row in endpoint_bad).items())
        ),
        "invariants": invariants,
        "scope": {
            "device": "CPU",
            "optimizer_run": False,
            "third_party_measurements_committed": False,
            "production_authorized": False,
        },
        "source_receipts": {
            "scripts/audit_pv17_sidis_endpoint.py": sha256_file(Path(__file__)),
            "tmdlab/models.py": sha256_file(
                Path(__file__).resolve().parents[1] / "tmdlab/models.py"
            ),
            "tmdlab/pv17.py": sha256_file(
                Path(__file__).resolve().parents[1] / "tmdlab/pv17.py"
            ),
        },
        "supersedes_campaign_next_gate": True,
        "next_gate": (
            "Resolve the HERMES K- current-theory sign failure and independently close "
            "the D0 Run-II normalized 40<Q<200 numerator/denominator contract before "
            "assembling or optimizing the ordered 8,059-observation likelihood."
        ),
    }
    if require_full_population and not all(invariants.values()):
        failed = [name for name, passed in invariants.items() if not passed]
        raise ValueError(f"PV17 SIDIS endpoint feasibility invariants failed: {failed}")
    receipt["identity"] = hashlib.sha256(
        canonical_json(receipt).encode("utf-8")
    ).hexdigest()
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-dir", type=Path, required=True)
    parser.add_argument("--campaign-receipt", type=Path, required=True)
    parser.add_argument("--endpoint", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("refuse to overwrite public endpoint-feasibility receipt")
    receipt = audit(
        args.campaign_dir,
        args.campaign_receipt,
        args.endpoint,
        args.result,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(canonical_json({"identity": receipt["identity"], "status": receipt["status"]}))


if __name__ == "__main__":
    main()
