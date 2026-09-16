#!/usr/bin/env python3
"""Build resumable current-theory point operators for all 7,990 PV17 SIDIS rows.

HERMES shards follow source tables.  Every COMPASS shard is one complete
normalization spectrum, including its fixed lowest-PhT denominator.  The
ignored campaign directory contains measurements/source identities; the public
receipt contains only aggregate counts, content hashes, and validation maxima.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.audit_pv17_sidis_domain import canonical_json
from scripts.run_pv17_sidis_point_pilot import (
    HADRON_MAP,
    TARGET_MAP,
    array_receipt,
    build_inventory,
    build_point_operator,
    concatenate_operators,
    load_foundation_read_only,
    point_density,
    sha256_bytes,
    sha256_file,
)
from tmdlab.models import Config as DNNConfig
from tmdlab.models import build as build_dnn
from tmdlab.pv17 import evaluate_sidis_point_arrays, validate_sidis_point_arrays


EXPECTED = {
    "rows": 7990,
    "HERMES": 1514,
    "COMPASS": 6476,
    "COMPASS_denominators": 224,
}


def source_table(source_id: str) -> str:
    if ":line" not in source_id:
        raise ValueError("PV17 source ID lacks line binding")
    return source_id.rsplit(":line", 1)[0]


def plan_shards(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = sorted(
        (
            row for row in rows
            if row.get("selected_by_kinematic_cuts") and row.get("process") == "SIDIS"
        ),
        key=lambda row: row["selected_index"],
    )
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    order: list[tuple[str, str]] = []
    for row in selected:
        if row["experiment"] == "HERMES":
            key = ("HERMES_source_table", source_table(row["source_id"]))
        elif row["experiment"] == "COMPASS":
            key = ("COMPASS_spectrum", row["normalization"]["group"])
        else:
            raise ValueError("unexpected PV17 SIDIS experiment")
        if key not in groups:
            order.append(key)
            groups[key] = []
        groups[key].append(row)
    shards = []
    for index, key in enumerate(order):
        members = groups[key]
        shards.append(
            {
                "index": index,
                "kind": key[0],
                "key_sha256": sha256_bytes(key[1].encode("utf-8")),
                "selected_indices": [row["selected_index"] for row in members],
                "rows": members,
            }
        )
    return shards


def campaign_plan(
    shards: list[dict[str, Any]], manifest_sha256: str, source_receipts: dict[str, Any]
) -> dict[str, Any]:
    body = {
        "schema": "pv17-current-regional-sidis-point-campaign-plan-v1",
        "pv17_manifest_sha256": manifest_sha256,
        "source_receipts": source_receipts,
        "numerical_rule": {
            "point_observable": "legacy PV17 dM/dPhT at published averages",
            "transition": "0.15--0.30 one-minus-quintic in qT/Q",
            "fraction_order": 4,
            "scalar_b_orders": [12, 24],
            "operator_b_order": 24,
            "b_stop_GeV_inv": 16.0,
            "Gaussian_control_g_GeV2": 0.25,
            "pdf_xmin": 0.003,
            "ff_zmin": 0.2,
        },
        "shards": [
            {key: value for key, value in shard.items() if key != "rows"}
            for shard in shards
        ],
    }
    body["identity"] = sha256_bytes(canonical_json(body).encode("utf-8"))
    return body


def shard_paths(directory: Path, index: int) -> tuple[Path, Path]:
    stem = f"shard-{index:04d}"
    return directory / f"{stem}.npz", directory / f"{stem}.json"


def verified_existing_shard(
    arrays_path: Path, receipt_path: Path, plan_identity: str, expected_indices: list[int]
) -> dict[str, Any] | None:
    partial_arrays = arrays_path.with_suffix(".partial.npz")
    partial_receipt = receipt_path.with_suffix(".partial.json")
    if arrays_path.is_file() and not receipt_path.exists() and partial_receipt.is_file():
        candidate = json.loads(partial_receipt.read_text(encoding="utf-8"))
        if receipt_identity_valid(candidate) and candidate.get("arrays", {}).get(
            "npz_sha256"
        ) == sha256_file(arrays_path):
            partial_receipt.replace(receipt_path)
    elif not arrays_path.exists() and not receipt_path.exists() \
            and partial_arrays.is_file() and partial_receipt.is_file():
        candidate = json.loads(partial_receipt.read_text(encoding="utf-8"))
        if receipt_identity_valid(candidate) and candidate.get("arrays", {}).get(
            "npz_sha256"
        ) == sha256_file(partial_arrays):
            partial_arrays.replace(arrays_path)
            partial_receipt.replace(receipt_path)
    if not arrays_path.exists() and not receipt_path.exists():
        return None
    if not arrays_path.is_file() or not receipt_path.is_file():
        raise ValueError(f"partial or non-file shard evidence: {arrays_path.stem}")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if not receipt_identity_valid(receipt):
        raise ValueError(f"shard receipt identity mismatch: {receipt_path}")
    if receipt.get("campaign_plan_identity") != plan_identity \
            or receipt.get("selected_indices") != expected_indices \
            or receipt.get("arrays", {}).get("npz_sha256") != sha256_file(arrays_path):
        raise ValueError(f"shard binding mismatch: {receipt_path}")
    with np.load(arrays_path, allow_pickle=False) as archive:
        arrays = {name: archive[name] for name in archive.files}
        validate_sidis_point_arrays(arrays)
        for name, value in arrays.items():
            if array_receipt(value) != receipt["arrays"]["manifest"][name]:
                raise ValueError(f"shard array manifest mismatch: {receipt_path}:{name}")
    return receipt


def build_shard(
    shard: dict[str, Any], services, dnn, plan_identity: str,
    arrays_path: Path, receipt_path: Path,
) -> dict[str, Any]:
    start = time.monotonic()
    operator_items = []
    records = []
    for row in shard["rows"]:
        key = (row["target"], row["detected_hadron"])
        target_service, proton_service = services[key]
        scalar = point_density(target_service, row)
        operator, metadata = build_point_operator(proton_service, target_service, row, scalar)
        operator_items.append((operator, metadata))
        records.append(
            {
                "selected_index": row["selected_index"],
                "experiment": row["experiment"],
                "target": row["target"],
                "detected_hadron": row["detected_hadron"],
                "contributes_to_published_point_count": row[
                    "contributes_to_published_point_count"
                ],
                "normalization_group_sha256": (
                    sha256_bytes(row["normalization"]["group"].encode("utf-8"))
                    if row["experiment"] == "COMPASS" else None
                ),
                "is_COMPASS_fixed_denominator": bool(
                    row.get("normalization", {}).get("is_fixed_denominator")
                ),
                "qT_over_Q": scalar["kinematics"]["qT_over_Q"],
                "transition_weight": scalar["transition_weight"],
                "nf_hard_and_recoil": scalar["nf_hard_and_recoil"],
                "nf_OPE_sampled": scalar["nf_OPE_sampled"],
                "Gaussian_prediction_per_dPhT": scalar["multiplicity_per_dPhT"],
                "Gaussian_absolute_recovery_error": metadata[
                    "Gaussian_absolute_recovery_error"
                ],
                "W_b_rule_refinement_abs": scalar["numerical_indicators"][
                    "W_b_rule_refinement_abs"
                ],
                "FO_fraction_abs_T_L": scalar["numerical_indicators"][
                    "FO_fraction_abs_T_L"
                ],
                "ASY_abs": scalar["numerical_indicators"]["ASY_abs"],
                "coordinates": metadata["coordinates"],
                "signed_weights": metadata["signed_weights"],
                "negative_weights": metadata["negative_weights"],
            }
        )

    arrays = concatenate_operators(operator_items)
    validate_sidis_point_arrays(arrays)
    with np.errstate(over="raise", invalid="raise"):
        replay = evaluate_sidis_point_arrays(dnn, arrays).detach().cpu().numpy()
    replay_error = float(np.max(np.abs(replay - arrays["Gaussian_controls"]), initial=0.0))
    direct_error = max((record["Gaussian_absolute_recovery_error"] for record in records), default=0.0)
    if replay_error >= 2e-12 or direct_error >= 2e-8 or not np.isfinite(replay).all():
        raise ValueError(
            f"shard Gaussian replay failed: direct={direct_error} current_DNN={replay_error}"
        )

    arrays_path.parent.mkdir(parents=True, exist_ok=True)
    partial_arrays = arrays_path.with_suffix(".partial.npz")
    partial_receipt = receipt_path.with_suffix(".partial.json")
    np.savez(partial_arrays, **arrays)
    receipt = {
        "schema": "pv17-current-regional-sidis-point-shard-v1",
        "campaign_plan_identity": plan_identity,
        "shard_index": shard["index"],
        "kind": shard["kind"],
        "key_sha256": shard["key_sha256"],
        "selected_indices": shard["selected_indices"],
        "records": records,
        "arrays": {
            "npz_sha256": sha256_file(partial_arrays),
            "manifest": {name: array_receipt(value) for name, value in arrays.items()},
        },
        "diagnostics": {
            "direct_Gaussian_maximum_absolute_recovery_error": direct_error,
            "current_DNN_Gaussian_maximum_absolute_replay_error": replay_error,
            "wall_seconds_informational": time.monotonic() - start,
        },
    }
    identity_body = dict(receipt)
    identity_body["diagnostics"] = dict(receipt["diagnostics"])
    identity_body["diagnostics"].pop("wall_seconds_informational")
    receipt["identity"] = sha256_bytes(canonical_json(identity_body).encode("utf-8"))
    # The durable receipt identity omits wall time; verified_existing_shard
    # mirrors that rule instead of treating runtime telemetry as science.
    partial_receipt.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    partial_arrays.replace(arrays_path)
    partial_receipt.replace(receipt_path)
    return receipt


def receipt_identity_valid(receipt: dict[str, Any]) -> bool:
    body = {key: value for key, value in receipt.items() if key != "identity"}
    body["diagnostics"] = dict(body["diagnostics"])
    body["diagnostics"].pop("wall_seconds_informational", None)
    return receipt.get("identity") == sha256_bytes(canonical_json(body).encode("utf-8"))


def aggregate_public_receipt(
    plan: dict[str, Any], shard_receipts: list[dict[str, Any]],
    source_receipts: dict[str, Any], build_unchanged: bool,
) -> dict[str, Any]:
    records = [record for receipt in shard_receipts for record in receipt["records"]]
    if sorted(record["selected_index"] for record in records) != sorted(
        index for shard in plan["shards"] for index in shard["selected_indices"]
    ):
        raise ValueError("completed shard row population differs from campaign plan")
    by_experiment = Counter(record["experiment"] for record in records)
    by_hadron = Counter(record["detected_hadron"] for record in records)
    by_target = Counter(record["target"] for record in records)
    roles = Counter(
        "full_additive" if record["transition_weight"] == 1.0
        else "FO_only" if record["transition_weight"] == 0.0
        else "transition"
        for record in records
    )
    denominator_active = {
        record["normalization_group_sha256"]: record["transition_weight"] > 0
        for record in records if record["is_COMPASS_fixed_denominator"]
    }
    scored_coupled = sum(
        record["contributes_to_published_point_count"] and (
            record["transition_weight"] > 0
            or record["experiment"] == "COMPASS"
            and denominator_active[record["normalization_group_sha256"]]
        )
        for record in records
    )
    array_bytes = sum(
        math.prod(spec["shape"]) * np.dtype(spec["dtype"]).itemsize
        for receipt in shard_receipts
        for spec in receipt["arrays"]["manifest"].values()
    )
    counts = {
        "selected_SIDIS_raw_rows": len(records),
        "scored_SIDIS_observations": sum(
            record["contributes_to_published_point_count"] for record in records
        ),
        "COMPASS_fixed_denominators": sum(
            record["is_COMPASS_fixed_denominator"] for record in records
        ),
        "raw_rows_with_DNN_W_operator": sum(
            record["transition_weight"] > 0 for record in records
        ),
        "raw_fixed_order_only_rows": roles["FO_only"],
        "scored_observations_DNN_coupled_directly_or_through_COMPASS_denominator": scored_coupled,
        "coordinates": sum(record["coordinates"] for record in records),
        "signed_weights": sum(record["signed_weights"] for record in records),
        "negative_weights": sum(record["negative_weights"] for record in records),
        "shards": len(shard_receipts),
        "array_bytes": array_bytes,
        "by_experiment": dict(sorted(by_experiment.items())),
        "by_hadron": dict(sorted(by_hadron.items())),
        "by_target": dict(sorted(by_target.items())),
        "by_matching_role": dict(sorted(roles.items())),
    }
    predictions = [record["Gaussian_prediction_per_dPhT"] for record in records]
    diagnostics = {
        "direct_Gaussian_maximum_absolute_recovery_error": max(
            record["Gaussian_absolute_recovery_error"] for record in records
        ),
        "current_DNN_Gaussian_maximum_absolute_replay_error": max(
            receipt["diagnostics"]["current_DNN_Gaussian_maximum_absolute_replay_error"]
            for receipt in shard_receipts
        ),
        "maximum_W_b_rule_refinement_abs": max(
            record["W_b_rule_refinement_abs"] for record in records
        ),
        "maximum_FO_fraction_abs": max(
            max(record["FO_fraction_abs_T_L"]) for record in records
        ),
        "maximum_ASY_abs": max(record["ASY_abs"] for record in records),
        "Gaussian_control_minimum": min(predictions),
        "Gaussian_control_maximum": max(predictions),
        "Gaussian_control_nonpositive_rows": sum(value <= 0 for value in predictions),
    }
    invariants = {
        "exact_7990_raw_rows": counts["selected_SIDIS_raw_rows"] == EXPECTED["rows"],
        "exact_experiment_counts": (
            by_experiment["HERMES"] == EXPECTED["HERMES"]
            and by_experiment["COMPASS"] == EXPECTED["COMPASS"]
        ),
        "exact_224_COMPASS_denominators": (
            counts["COMPASS_fixed_denominators"] == EXPECTED["COMPASS_denominators"]
        ),
        "all_predictions_finite": all(math.isfinite(value) for value in predictions),
        "direct_Gaussian_recovery_below_2e_minus_8": (
            diagnostics["direct_Gaussian_maximum_absolute_recovery_error"] < 2e-8
        ),
        "current_DNN_Gaussian_replay_below_2e_minus_12": (
            diagnostics["current_DNN_Gaussian_maximum_absolute_replay_error"] < 2e-12
        ),
        "foundation_build_inventory_unchanged": build_unchanged,
    }
    if not all(invariants.values()):
        raise ValueError(f"PV17 full SIDIS operator invariant failed: {invariants}")
    receipt = {
        "schema": "pv17-current-regional-sidis-point-campaign-v1",
        "status": "all_7990_SIDIS_point_operators_built_and_CPU_replayed",
        "campaign_plan_identity": plan["identity"],
        "source_receipts": source_receipts,
        "scope": {
            "observable": "legacy PV17 dM/dPhT at published average x,z,Q2,PhT",
            "theory": "current regional unprimed N3LL W plus NLO recoil and NLO DIS denominator",
            "production_authorized": False,
            "heavy_threshold_complete": False,
            "GPU_used": False,
            "optimizer_run": False,
            "Gaussian_control_is_not_a_fit": True,
        },
        "counts": counts,
        "diagnostics": diagnostics,
        "invariants": invariants,
        "shard_binding": {
            "identities_ordered_sha256": sha256_bytes(
                canonical_json([receipt["identity"] for receipt in shard_receipts]).encode("utf-8")
            ),
            "npz_hashes_ordered_sha256": sha256_bytes(
                canonical_json(
                    [receipt["arrays"]["npz_sha256"] for receipt in shard_receipts]
                ).encode("utf-8")
            ),
        },
        "next_gate": (
            "Construct the 8 missing D0 Run-II operators and the ordered 8059-row ratio/metric "
            "adapter, then run stratified independent prediction, covariance, gradient, and CPU/GPU checks."
        ),
    }
    receipt["identity"] = sha256_bytes(canonical_json(receipt).encode("utf-8"))
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--foundation-root", type=Path, required=True)
    parser.add_argument("--prebuilt-library", type=Path, required=True)
    parser.add_argument("--prebuilt-provenance-receipt", type=Path, required=True)
    parser.add_argument("--campaign-dir", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    parser.add_argument("--stop-after-new-shards", type=int)
    args = parser.parse_args()
    if args.stop_after_new_shards is not None and args.stop_after_new_shards < 1:
        raise ValueError("stop-after-new-shards must be positive")
    if args.receipt_out.exists():
        raise ValueError("refuse to overwrite public PV17 SIDIS campaign receipt")

    manifest_payload = args.manifest.read_bytes()
    rows = [json.loads(line) for line in manifest_payload.splitlines() if line.strip()]
    shards = plan_shards(rows)
    pre_inventory = build_inventory(args.foundation_root)
    runtime = load_foundation_read_only(
        args.foundation_root, args.prebuilt_library, args.prebuilt_provenance_receipt
    )
    root = Path(__file__).resolve().parents[1]
    source_receipts = {
        "pv17_manifest_sha256": sha256_bytes(manifest_payload),
        "prebuilt_binary_sha256": runtime["binary_sha256"],
        "prebuilt_provenance_receipt_sha256": runtime["provenance_receipt_sha256"],
        "producer_sources": {
            "scripts/build_pv17_sidis_point_operators.py": sha256_file(Path(__file__)),
            "scripts/run_pv17_sidis_point_pilot.py": sha256_file(
                root / "scripts/run_pv17_sidis_point_pilot.py"
            ),
            "tmdlab/pv17.py": sha256_file(root / "tmdlab/pv17.py"),
            "tmdlab/models.py": sha256_file(root / "tmdlab/models.py"),
        },
        "foundation_build_inventory_sha256": sha256_bytes(
            canonical_json(pre_inventory).encode("utf-8")
        ),
        "current_theory_python_sources": {
            name: sha256_file(runtime["root"] / name)
            for name in (
                "src/bttmd_foundation/sidis_common_matching.py",
                "src/bttmd_foundation/sidis_common_w.py",
                "src/bttmd_foundation/sidis_uv_subtraction.py",
                "work/conditional_delivered_sidis_pilot/pilot.py",
                "work/direct_fit_launch_sidis/flavors.py",
                "work/regional_matching/coupling.py",
                "work/regional_matching/panel.py",
                "work/regional_matching/pilot.py",
                "work/regional_matching/service.py",
                "work/regional_matching/w.py",
            )
        },
    }
    plan = campaign_plan(shards, source_receipts["pv17_manifest_sha256"], source_receipts)
    args.campaign_dir.mkdir(parents=True, exist_ok=True)
    plan_path = args.campaign_dir / "plan.json"
    if plan_path.exists():
        if json.loads(plan_path.read_text(encoding="utf-8")) != plan:
            raise ValueError("existing PV17 SIDIS campaign plan differs")
    else:
        plan_path.write_text(
            json.dumps(plan, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )

    existing = {}
    pending = []
    for shard in shards:
        arrays_path, receipt_path = shard_paths(args.campaign_dir, shard["index"])
        receipt = verified_existing_shard(
            arrays_path, receipt_path, plan["identity"], shard["selected_indices"]
        )
        if receipt is None:
            pending.append(shard)
        else:
            if not receipt_identity_valid(receipt):
                raise ValueError(f"shard scientific identity mismatch: {receipt_path}")
            existing[shard["index"]] = receipt
    print(json.dumps({"phase": "resume_audit", "shards": len(shards),
                      "complete": len(existing), "pending": len(pending)}), flush=True)

    if pending:
        import lhapdf
        from work.regional_matching.service import RegionalConfig, RegionalService

        lhapdf.setVerbosity(0)
        combinations = sorted(
            {(row["target"], row["detected_hadron"])
             for shard in pending for row in shard["rows"]}
        )
        base_services = {}
        services = {}
        try:
            for target_name, hadron_name in combinations:
                hadron = HADRON_MAP[hadron_name]
                target = TARGET_MAP[target_name]
                base_key = (target, hadron)
                if base_key not in base_services:
                    base_services[base_key] = RegionalService(
                        RegionalConfig(target=target, hadron=hadron, pdf_xmin=0.003, ff_zmin=0.2)
                    )
                proton_key = ("proton", hadron)
                if proton_key not in base_services:
                    base_services[proton_key] = RegionalService(
                        RegionalConfig(target="proton", hadron=hadron, pdf_xmin=0.003, ff_zmin=0.2)
                    )
                services[(target_name, hadron_name)] = (
                    base_services[base_key], base_services[proton_key]
                )
            dnn = build_dnn(DNNConfig(width=8), seed=20260915).double().cpu()
            built = 0
            for shard in pending:
                arrays_path, receipt_path = shard_paths(args.campaign_dir, shard["index"])
                receipt = build_shard(
                    shard, services, dnn, plan["identity"], arrays_path, receipt_path
                )
                existing[shard["index"]] = receipt
                built += 1
                print(json.dumps({"phase": "shard_complete", "index": shard["index"],
                                  "rows": len(shard["rows"]), "new_complete": built,
                                  "remaining": len(pending) - built}), flush=True)
                if args.stop_after_new_shards is not None and built >= args.stop_after_new_shards:
                    break
            for service in base_services.values():
                service.verify_unchanged()
        finally:
            for service in base_services.values():
                service.close()

    if build_inventory(args.foundation_root) != pre_inventory:
        raise ValueError("foundation regional build inventory changed during campaign")
    if len(existing) != len(shards):
        print(json.dumps({"phase": "bounded_stop", "complete": len(existing),
                          "pending": len(shards) - len(existing)}), flush=True)
        return
    ordered_receipts = [existing[index] for index in range(len(shards))]
    public = aggregate_public_receipt(plan, ordered_receipts, source_receipts, True)
    args.receipt_out.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_out.write_text(
        json.dumps(public, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"phase": "complete", "identity": public["identity"],
                      "rows": public["counts"]["selected_SIDIS_raw_rows"]}), flush=True)


if __name__ == "__main__":
    main()
