#!/usr/bin/env python3
"""Audit the PV17/D0 Run-II normalized-observable contract without evaluation.

The public receipt contains only row identities and integration geometry.  The
third-party measurements remain in the ignored PV17 manifest and are used only
to verify the source crosswalk against the foundation's compile-only plan.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED_BLOCKERS = {
    "D0_RUN_2.full_normalized_covariance",
    "D0_RUN_2.normalized_denominator_provider",
    "D0_RUN_2.qed_conformance",
    "D0_RUN_2.provider_and_numerics",
    "D0_RUN_2.stage0_mass_support_conflict",
    "D0_RUN_2.unfolding_covariance",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_embedded_hash(value: dict[str, Any], field: str) -> bool:
    payload = dict(value)
    expected = payload.pop(field)
    return canonical_sha256(payload) == expected


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], str]:
    payload = path.read_bytes()
    rows = [json.loads(line) for line in payload.splitlines() if line.strip()]
    return rows, hashlib.sha256(payload).hexdigest()


def crosswalk_d0_rows(
    manifest_rows: list[dict[str, Any]], plan: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, bool]]:
    pv17 = [row for row in manifest_rows if row["experiment"] == "D0_RunII"]
    compiled = plan["compiled_rows"]
    if len(pv17) != len(compiled):
        raise ValueError("PV17 and corrected D0 Run-II populations differ")

    selected_crosswalk = []
    source_values_match = True
    source_errors_match = True
    display_points_match = True
    selected_are_first_eight = True
    for index, (legacy, current) in enumerate(zip(pv17, compiled)):
        raw = legacy["raw"]
        published = current["published_observable"]
        errors = current["uncertainty_evidence"]["publication_table_components"]
        source_values_match &= float(raw["value"]) == float(published["value"])
        source_errors_match &= (
            float(raw["statistical_or_published_combined_error"])
            == float(errors["statistical_absolute_1_per_GeV"])
            and float(raw["systematic_error"])
            == float(errors["systematic_absolute_1_per_GeV"])
        )
        display_points_match &= float(raw["qT_GeV"]) == float(
            published["representative_qT_GeV"]
        )
        if legacy["selected_by_kinematic_cuts"]:
            selected_are_first_eight &= index == len(selected_crosswalk)
            selected_crosswalk.append(
                {
                    "selected_index": int(legacy["selected_index"]),
                    "candidate_observation_id": current["candidate_observation_id"],
                    "source_row_index": int(current["source_row_index"]),
                    "qT_bin_GeV": current["support"]["qT"],
                    "representative_qT_GeV": float(published["representative_qT_GeV"]),
                }
            )

    checks = {
        "all_23_source_central_values_match": source_values_match,
        "all_23_source_error_components_match": source_errors_match,
        "all_23_representative_qT_values_match": display_points_match,
        "selected_rows_are_first_8_source_bins": (
            selected_are_first_eight and len(selected_crosswalk) == 8
        ),
    }
    return selected_crosswalk, checks


def audit(args: argparse.Namespace) -> dict[str, Any]:
    manifest_rows, pv17_manifest_sha256 = load_jsonl(args.pv17_manifest)
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    plan_manifest = json.loads(args.plan_manifest.read_text(encoding="utf-8"))
    ledger = json.loads(args.dependency_ledger.read_text(encoding="utf-8"))
    readiness = json.loads(args.readiness_contract.read_text(encoding="utf-8"))

    selected_crosswalk, source_checks = crosswalk_d0_rows(manifest_rows, plan)
    output = next(
        item
        for item in plan_manifest["outputs"]
        if item.get("dataset_id") == "DY:D0_RUN_2"
    )
    dependency_by_id = {item["id"]: item for item in ledger["dependencies"]}
    family = next(
        item for item in readiness["families"] if item["id"] == "dy_d0_run2_normalized"
    )
    block = plan["normalization_blocks"][0]
    blocker_ids = {item["blocker_id"] for item in plan["blockers"]}
    row_ids = plan["row_ids"]

    row_hashes_valid = all(
        validate_embedded_hash(row, "row_plan_sha256") for row in plan["compiled_rows"]
    )
    action_checks = all(
        row["observable_action"]["formula"] == "prediction_i=N_i/(Delta_qT_i*D)"
        and row["observable_action"]["integrate_before_division"] is True
        and row["observable_action"][
            "renormalize_over_selected_or_low_qT_rows_allowed"
        ]
        is False
        and row["observable_action"]["dependent_row_ids"] == row_ids
        and row["numerator_action"]["kind"] == "exact_bin_integral"
        and row["numerator_action"]["bin_center_or_representative_point_substitution_allowed"]
        is False
        for row in plan["compiled_rows"]
    )
    source_support = plan["dataset_contract"]["mass_support_GeV"]
    stage0_support = plan["dataset_contract"]["stage0_mass_support_GeV"]
    dimensions = family["dimensions"]

    invariants = {
        **source_checks,
        "compile_plan_has_exactly_23_ordered_rows": row_ids
        == [f"obs:D0_RUN_2:{index}" for index in range(23)],
        "plan_hash_valid": validate_embedded_hash(plan, "plan_sha256"),
        "plan_source_manifest_hash_valid": canonical_sha256(plan["source_manifest"])
        == plan["source_manifest_sha256"],
        "plan_manifest_hash_valid": validate_embedded_hash(
            plan_manifest, "manifest_payload_sha256"
        ),
        "row_order_hash_valid": canonical_sha256(row_ids) == plan["row_order_sha256"],
        "all_row_hashes_valid": row_hashes_valid,
        "normalization_block_hash_valid": validate_embedded_hash(block, "block_sha256"),
        "plan_manifest_file_hash_matches": output["file_sha256"] == sha256_file(args.plan),
        "plan_manifest_identity_matches": output["plan_sha256"] == plan["plan_sha256"],
        "corrected_source_support_is_40_to_200_GeV": source_support
        == {"low": 40.0, "high": 200.0},
        "legacy_stage0_support_is_70_to_110_GeV": stage0_support
        == {"low": 70.0, "high": 110.0},
        "pair_rapidity_is_inclusive": plan["dataset_contract"]["pair_rapidity"]
        == "inclusive_all_rapidity",
        "ratio_of_integrals_actions_are_complete": action_checks,
        "denominator_uses_full_physical_recoil": block["qT_support"]
        == "all_physical_recoil_not_only_published_or_selected_rows",
        "selected_subset_is_not_renormalized": block["renormalize_to_selected_rows"]
        is False,
        "required_blockers_are_explicit": blocker_ids == REQUIRED_BLOCKERS,
        "plan_remains_compile_only": (
            plan["state"] == "blocked"
            and plan["invariants"]["theory_evaluated"] is False
            and plan["invariants"]["predictions_written"] is False
            and plan["closure_disposition"]["evaluation_ready"] is False
        ),
        "registry_conflict_is_actionable": dependency_by_id[
            "DATA-D0-RUN2-REGISTRY-CONFLICT"
        ]["status"]
        == "actionable",
        "tevatron_covariance_is_open_high": dependency_by_id["COV-TEVATRON"][
            "status"
        ]
        == "open_high",
        "readiness_still_blocks_source_and_covariance": (
            dimensions["source_identity"]["status"] == "blocked"
            and dimensions["covariance"]["status"] == "blocked"
        ),
    }
    if not all(invariants.values()):
        failed = [name for name, passed in invariants.items() if not passed]
        raise ValueError(f"D0 Run-II normalized-contract invariant failed: {failed}")

    receipt = {
        "schema": "pv17-d0-runii-normalized-contract-audit-v1",
        "status": "source_crosswalk_and_compile_actions_closed_physical_evaluation_blocked",
        "scope": {
            "dataset": "DY:D0_RUN_2",
            "published_observable": "(1/sigma)*d_sigma/d_qT",
            "prediction_formula": "N_i/(Delta_qT_i*D)",
            "current_theory_accuracy": "N3LL_unprimed_plus_Born_relative_NNLO_DY",
            "source_mass_support_GeV": source_support,
            "stage0_conflicting_mass_support_GeV": stage0_support,
            "pair_rapidity": plan["dataset_contract"]["pair_rapidity"],
            "measurements_written_to_receipt": False,
        },
        "counts": {
            "source_rows": len(plan["compiled_rows"]),
            "PV17_selected_rows": len(selected_crosswalk),
            "normalization_dependent_rows_per_numerator": len(row_ids),
            "open_blockers": len(plan["blockers"]),
        },
        "selected_crosswalk": selected_crosswalk,
        "normalization_contract": {
            "block_id": block["block_id"],
            "mass_support_GeV": block["mass_support_GeV"],
            "pair_rapidity": block["pair_rapidity"],
            "qT_support": block["qT_support"],
            "published_qT_bins_GeV": block["published_qT_bins_GeV"],
            "same_provider_family_as_numerators": block[
                "same_provider_family_as_numerators"
            ],
            "recompute_for_every_theory_member": block[
                "recompute_for_every_central_scale_PDF_EW_QED_and_NP_member"
            ],
            "renormalize_to_selected_rows": block["renormalize_to_selected_rows"],
            "source_status": block["source_status"],
        },
        "closure": {
            "closed": [
                "all 23 PV17 source rows match the corrected compile plan",
                "the eight retained PV17 rows map to source bins 0 through 7",
                "exact bin numerator and full-support denominator actions are specified",
                "selected low-qT rows are never renormalized",
            ],
            "open": plan["blockers"],
            "classification": (
                "not_an_eight_point_operator_coding_gap; physical evaluation and the exact "
                "likelihood remain blocked by provider, registry, QED, and covariance inputs"
            ),
        },
        "dependency_status": {
            key: dependency_by_id[key]
            for key in ("DATA-D0-RUN2-REGISTRY-CONFLICT", "COV-TEVATRON")
        },
        "readiness_dimensions": dimensions,
        "invariants": invariants,
        "source_receipts": {
            "pv17_manifest_sha256": pv17_manifest_sha256,
            "compile_plan_sha256": sha256_file(args.plan),
            "compile_plan_identity": plan["plan_sha256"],
            "compile_plan_manifest_sha256": sha256_file(args.plan_manifest),
            "dependency_ledger_sha256": sha256_file(args.dependency_ledger),
            "readiness_contract_sha256": sha256_file(args.readiness_contract),
            "producer_sha256": sha256_file(Path(__file__)),
        },
        "next_gate": (
            "Revise the immutable D0 Run-II registry to 40<Q<200 GeV inclusive-rapidity "
            "support, bind and converge same-family numerator and inclusive NNLO denominator "
            "providers with resolved QED conventions, and recover or explicitly approve an "
            "approximation to the normalized unfolding covariance before evaluation."
        ),
    }
    receipt["identity"] = canonical_sha256(receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pv17-manifest", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-manifest", type=Path, required=True)
    parser.add_argument("--dependency-ledger", type=Path, required=True)
    parser.add_argument("--readiness-contract", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args()
    receipt = audit(args)
    args.receipt_out.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_out.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
