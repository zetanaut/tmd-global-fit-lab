#!/usr/bin/env python3
"""Audit reusable current-theory operator coverage for the PV17 raw rows.

This does not construct or evaluate an operator.  It binds the exact PV17
selected-row geometry to the already prepared current DY/Z source inventory and
the completed operator catalog, then records which rows can be reused without a
physics change and which require new construction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


EXPERIMENT_TO_CURRENT_DATASET = {
    "E288_200": "E288_200",
    "E288_300": "E288_300",
    "E288_400": "E288_400",
    "E605": "E605",
    "CDF_RunI": "CDF_RUN_1",
    "D0_RunI": "D0_RUN_1",
    "CDF_RunII": "CDF_RUN_2",
    "D0_RunII": "D0_RUN_2",
}

BLOCKED_D0_RUN_II_STATUS = "blocked_normalized_fiducial_numerator_denominator_contract"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def jsonl(path: Path) -> tuple[list[dict[str, Any]], str]:
    payload = path.read_bytes()
    return [json.loads(line) for line in payload.splitlines() if line.strip()], sha256_bytes(payload)


def geometry_key_for_current(row: dict[str, Any]) -> tuple[str, float, float | None]:
    dataset = row["dataset_id"].removeprefix("DY:")
    q_value = None if dataset.startswith(("CDF", "D0")) else round(
        float(row["kinematics"]["QM"]), 10
    )
    return dataset, round(float(row["kinematics"]["qT"]), 10), q_value


def geometry_key_for_pv17(row: dict[str, Any]) -> tuple[str, float, float | None]:
    dataset = EXPERIMENT_TO_CURRENT_DATASET[row["experiment"]]
    q_value = None if row["process"] == "Z" else round(float(row["raw"]["Q_GeV"]), 10)
    return dataset, round(float(row["raw"]["qT_GeV"]), 10), q_value


def coverage_status(
    row: dict[str, Any], prepared: dict[str, Any] | None, existing: dict[str, Any]
) -> str:
    if row["process"] == "SIDIS":
        return "new_current_theory_point_operator_required"
    if prepared is None:
        return "missing_current_source_geometry"
    if row["experiment"] == "D0_RunII":
        # This experiment published a normalized shape.  The inherited card's
        # 70--110 GeV support and theory-derived absolute conversion cannot be
        # used with current theory.  A corrected source numerator and a
        # model-dependent normalization denominator are both required.
        return BLOCKED_D0_RUN_II_STATUS
    if prepared["observation_id"] in existing:
        return "reuse_completed_current_theory_operator_with_unit_adapter"
    return "new_current_theory_DY_Z_operator_required"


def audit_coverage(
    pv17_rows: Iterable[dict[str, Any]],
    prepared_rows: Iterable[dict[str, Any]],
    catalog: dict[str, Any],
) -> dict[str, Any]:
    selected = [row for row in pv17_rows if row["selected_by_kinematic_cuts"]]
    prepared_by_geometry: dict[tuple[str, float, float | None], dict[str, Any]] = {}
    for row in prepared_rows:
        key = geometry_key_for_current(row)
        if key in prepared_by_geometry:
            raise ValueError(f"current prepared geometry is not unique: {key}")
        prepared_by_geometry[key] = row
    existing = {entry["observation_id"]: entry["reference"] for entry in catalog["coverage"]}

    status_counts: Counter[str] = Counter()
    by_experiment: Counter[tuple[str, str]] = Counter()
    reused_references: list[dict[str, Any]] = []
    missing_geometry: list[str] = []
    low_energy_value_relative_differences: list[float] = []
    exact_z_value_differences: list[float] = []

    for row in selected:
        prepared = None
        if row["process"] == "SIDIS":
            status = coverage_status(row, prepared, existing)
        else:
            prepared = prepared_by_geometry.get(geometry_key_for_pv17(row))
            status = coverage_status(row, prepared, existing)
            if status == "missing_current_source_geometry":
                missing_geometry.append(row["source_id"])
            elif status == "reuse_completed_current_theory_operator_with_unit_adapter":
                reused_references.append(existing[prepared["observation_id"]])

            if prepared is not None and row["process"] == "DY":
                # The current source uses legacy CS=A/PreFactor, while PV17
                # stores A in units of 1e-36 cm^2/GeV^2.  This check diagnoses
                # source-table identity only; the PV17 central values remain
                # authoritative for the new metric.
                current_a = float(prepared["value"]) * float(
                    prepared["transformation"]["PreFactor"]
                )
                pv17_a = float(row["raw"]["value"]) * 1e36
                low_energy_value_relative_differences.append(
                    abs(current_a - pv17_a) / max(abs(pv17_a), 1e-300)
                )
            elif prepared is not None:
                current_value = float(prepared["value"])
                pv17_value = float(row["transformed"]["value"])
                if row["experiment"] != "D0_RunII":
                    exact_z_value_differences.append(abs(current_value - pv17_value))

        status_counts[status] += 1
        by_experiment[(row["experiment"], status)] += 1

    if missing_geometry:
        raise ValueError(f"missing current DY/Z prepared geometries: {missing_geometry[:3]}")

    unique_reused = {reference["identity"]: reference for reference in reused_references}
    invariants = {
        "selected_raw_rows_equal_8283": len(selected) == 8283,
        "all_293_DY_Z_rows_have_current_source_geometry": sum(
            row["process"] in ("DY", "Z") for row in selected
        )
        == 293,
        "completed_operator_reuse_count_equal_285": len(unique_reused) == 285,
        "blocked_D0_RunII_normalized_contract_count_equal_8": by_experiment[
            ("D0_RunII", BLOCKED_D0_RUN_II_STATUS)
        ]
        == 8,
        "new_SIDIS_point_operator_count_equal_7990": status_counts[
            "new_current_theory_point_operator_required"
        ]
        == 7990,
        "existing_Z_central_values_match_exactly": max(exact_z_value_differences, default=0.0)
        == 0.0,
        "low_energy_source_values_match_within_rounding": max(
            low_energy_value_relative_differences, default=0.0
        )
        < 1e-6,
        "coverage_sums_to_selected_raw_rows": sum(status_counts.values()) == len(selected),
    }
    if not all(invariants.values()):
        raise ValueError(f"PV17 operator-coverage invariant failed: {invariants}")

    reference_digest = sha256_bytes(
        canonical_json(
            [
                {
                    "identity": reference["identity"],
                    "json_sha256": reference["json_sha256"],
                    "npz_sha256": reference["npz_sha256"],
                    "observation_id": reference["row"]["observation_id"],
                }
                for reference in sorted(
                    unique_reused.values(), key=lambda item: item["row"]["observation_id"]
                )
            ]
        ).encode("utf-8")
    )
    return {
        "counts": {
            "selected_raw_rows": len(selected),
            "existing_current_theory_operators_reusable": len(unique_reused),
            "nonreusable_raw_rows": len(selected) - len(unique_reused),
            "new_SIDIS_point_operators_required": status_counts[
                "new_current_theory_point_operator_required"
            ],
            "blocked_D0_RunII_rows": by_experiment[
                ("D0_RunII", BLOCKED_D0_RUN_II_STATUS)
            ],
        },
        "by_experiment_and_status": [
            {"experiment": experiment, "status": status, "rows": count}
            for (experiment, status), count in sorted(by_experiment.items())
        ],
        "reused_reference_digest_sha256": reference_digest,
        "current_model_contract_identity": catalog["model_contract"]["identity"],
        "diagnostics": {
            "max_low_energy_source_value_relative_rounding_difference": max(
                low_energy_value_relative_differences, default=0.0
            ),
            "max_existing_Z_central_value_absolute_difference": max(
                exact_z_value_differences, default=0.0
            ),
        },
        "invariants": invariants,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pv17-manifest", type=Path, required=True)
    parser.add_argument("--prepared-dy-rows", type=Path, required=True)
    parser.add_argument("--operator-catalog", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args()

    pv17_rows, pv17_manifest_sha256 = jsonl(args.pv17_manifest)
    prepared_rows, prepared_rows_sha256 = jsonl(args.prepared_dy_rows)
    catalog_payload = args.operator_catalog.read_bytes()
    catalog = json.loads(catalog_payload)
    result = audit_coverage(pv17_rows, prepared_rows, catalog)
    receipt = {
        "schema": "pv17-current-theory-operator-coverage-v1",
        "status": "coverage_closed_SIDIS_construction_open_D0II_contract_blocked",
        "source_receipts": {
            "pv17_manifest_sha256": pv17_manifest_sha256,
            "current_prepared_DY_rows_sha256": prepared_rows_sha256,
            "current_operator_catalog_sha256": sha256_bytes(catalog_payload),
            "current_operator_catalog_identity": catalog["identity"],
        },
        **result,
        "construction": {
            "reused_low_energy_DY_adapter": (
                "multiply the existing legacy-CS operator, including its fixed term, by "
                "PreFactor*1e-36 to predict the PV17 E*d3sigma/dp3 units"
            ),
            "reused_CDF_D0_RunI_adapter": "identity pb/GeV; do not apply PV17 fixed theory-normalization factors",
            "D0_RunII": (
                "blocked: retain the published normalized shape and construct a current-theory numerator/"
                "normalization-denominator quotient on corrected source support; do not use the inherited "
                "70--110 GeV card or PV17's theory-derived 255.8 pb conversion"
            ),
            "new_SIDIS": (
                "construct current matched-theory multiplicities at the PV17 published average "
                "x,z,Q2,PhT points; do not substitute the current bin-integrated HEPData operators"
            ),
            "COMPASS": (
                "construct all 6476 retained raw multiplicities first, then form 6252 "
                "numerator/lowest-PhT prediction ratios"
            ),
        },
        "next_gate": (
            "Complete and independently review the D0 Run-II source-support and normalized "
            "numerator/denominator contract; SIDIS point-operator construction can proceed separately."
        ),
    }
    receipt["identity"] = sha256_bytes(canonical_json(receipt).encode("utf-8"))
    args.receipt_out.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_out.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
