#!/usr/bin/env python3
"""Build the PV17 8,059-observation metric contract without theory calls.

The input is the local, ignored row manifest produced by
``audit_pv17_row_closure.py``.  The output arrays also contain third-party
measurements and therefore remain local/ignored.  A public receipt records only
counts, formulas, invariants, and content hashes.

The metric is represented as

    C_eff(t0) = diag(D) + U_compass U_compass^T
                + (F_norm * t0[:, None]) (F_norm * t0[:, None])^T.

``t0`` is deliberately not supplied by the data audit.  It must be a named,
hash-bound prediction from the current matched-theory operator.  This avoids
using the measured central values to define multiplicative covariance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import numpy as np


DY_NORMALIZATION_FRACTIONS = {
    "E288_200": 0.25,
    "E288_300": 0.25,
    "E288_400": 0.25,
    "E605": 0.15,
}

Z_NORMALIZATION_FRACTIONS = {
    "CDF_RunI": 0.039,
    "D0_RunI": 0.044,
    "CDF_RunII": 0.058,
}

EXPECTED_EXPERIMENT_COUNTS = {
    "HERMES": 1514,
    "COMPASS": 6252,
    "E288_400": 78,
    "E288_300": 45,
    "E288_200": 45,
    "E605": 35,
    "CDF_RunI": 31,
    "D0_RunI": 14,
    "CDF_RunII": 37,
    "D0_RunII": 8,
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def array_receipt(array: np.ndarray) -> dict[str, Any]:
    contiguous = np.ascontiguousarray(array)
    descriptor = {
        "dtype": contiguous.dtype.str,
        "shape": list(contiguous.shape),
        "bytes_sha256": sha256_bytes(contiguous.tobytes(order="C")),
    }
    descriptor["identity"] = sha256_bytes(canonical_json(descriptor).encode("utf-8"))
    return descriptor


def read_manifest(path: Path) -> tuple[list[dict[str, Any]], str]:
    payload = path.read_bytes()
    rows = [json.loads(line) for line in payload.splitlines() if line.strip()]
    if not rows:
        raise ValueError("empty PV17 row manifest")
    return rows, sha256_bytes(payload)


def ordered_selected_and_scored(
    rows: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected = sorted(
        (row for row in rows if row["selected_by_kinematic_cuts"]),
        key=lambda row: row["selected_index"],
    )
    scored = sorted(
        (row for row in rows if row["contributes_to_published_point_count"]),
        key=lambda row: row["published_point_index"],
    )
    if [row["selected_index"] for row in selected] != list(range(1, len(selected) + 1)):
        raise ValueError("selected row indices are not contiguous")
    if [row["published_point_index"] for row in scored] != list(range(1, len(scored) + 1)):
        raise ValueError("scored row indices are not contiguous")
    return selected, scored


def _primary_z_error(row: dict[str, Any]) -> float:
    transformed = row["transformed"]
    return float(
        transformed.get(
            "statistical_error", transformed.get("statistical_or_published_combined_error")
        )
    )


def build_metric_arrays(
    rows: Iterable[dict[str, Any]], *, require_full_population: bool = True
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    selected, scored = ordered_selected_and_scored(rows)
    n = len(scored)
    selected_by_id = {row["source_id"]: row for row in selected}
    if len(selected_by_id) != len(selected):
        raise ValueError("selected source IDs are not unique")

    compass_group_order: list[str] = []
    for row in selected:
        if row["experiment"] == "COMPASS":
            group = row["normalization"]["group"]
            if group not in compass_group_order:
                compass_group_order.append(group)
    compass_group_column = {group: index for index, group in enumerate(compass_group_order)}

    normalization_groups = list(DY_NORMALIZATION_FRACTIONS) + list(Z_NORMALIZATION_FRACTIONS)
    normalization_column = {group: index for index, group in enumerate(normalization_groups)}

    data = np.empty(n, dtype=np.float64)
    diagonal = np.empty(n, dtype=np.float64)
    compass_responses = np.zeros((n, len(compass_group_order)), dtype=np.float64)
    normalization_fractions = np.zeros((n, len(normalization_groups)), dtype=np.float64)
    selected_indices = np.empty(n, dtype=np.int64)
    process_codes = np.empty(n, dtype=np.int8)
    process_code = {"SIDIS": 0, "DY": 1, "Z": 2}
    historical_diagonal_variance = np.empty(n, dtype=np.float64)

    compass_marginal_checks: list[float] = []
    dyz_marginal_checks: list[float] = []
    d0_run_ii_rows = 0
    experiment_counts: Counter[str] = Counter()

    for output_index, row in enumerate(scored):
        raw = row["raw"]
        transformed = row["transformed"]
        experiment = row["experiment"]
        experiment_counts[experiment] += 1
        selected_indices[output_index] = row["selected_index"] - 1
        process_codes[output_index] = process_code[row["process"]]

        if experiment == "HERMES":
            stat = float(raw["statistical_error"])
            syst = float(raw["systematic_error"])
            data[output_index] = float(raw["value"])
            diagonal[output_index] = stat * stat + syst * syst
            historical_diagonal_variance[output_index] = diagonal[output_index]
        elif experiment == "COMPASS":
            denominator = selected_by_id[row["normalization"]["denominator_source_id"]]
            denominator_raw = denominator["raw"]
            m0 = float(denominator_raw["value"])
            value = float(raw["value"])
            ratio = value / m0
            numerator_variance = float(raw["statistical_error"]) ** 2 + float(
                raw["systematic_error"]
            ) ** 2
            denominator_variance = float(denominator_raw["statistical_error"]) ** 2 + float(
                denominator_raw["systematic_error"]
            ) ** 2
            data[output_index] = ratio
            diagonal[output_index] = numerator_variance / (m0 * m0)
            response = ratio * math.sqrt(denominator_variance) / m0
            compass_responses[
                output_index, compass_group_column[row["normalization"]["group"]]
            ] = response
            historical_diagonal_variance[output_index] = (
                float(transformed["statistical_error"]) ** 2
                + float(transformed["systematic_error"]) ** 2
            )
            compass_marginal_checks.append(
                abs(
                    diagonal[output_index]
                    + response * response
                    - historical_diagonal_variance[output_index]
                )
            )
            if not math.isclose(data[output_index], float(transformed["value"]), rel_tol=2e-15):
                raise ValueError(f"COMPASS ratio mismatch: {row['source_id']}")
        elif row["process"] == "DY":
            stat = float(raw["statistical_error"])
            fraction = DY_NORMALIZATION_FRACTIONS[experiment]
            data[output_index] = float(raw["value"])
            diagonal[output_index] = stat * stat
            normalization_fractions[output_index, normalization_column[experiment]] = fraction
            historical_diagonal_variance[output_index] = float(
                transformed["total_diagonal_error"]
            ) ** 2
            dyz_marginal_checks.append(
                abs(
                    diagonal[output_index]
                    + (fraction * data[output_index]) ** 2
                    - historical_diagonal_variance[output_index]
                )
            )
        elif experiment == "D0_RunII":
            # D0 published a normalized shape.  PV17 multiplied it by a
            # theory-derived 255.8 pb factor, but this baseline uses current
            # theory and must predict its own numerator and denominator.
            primary = float(raw["statistical_or_published_combined_error"])
            syst = float(raw["systematic_error"])
            data[output_index] = float(raw["value"])
            diagonal[output_index] = primary * primary + syst * syst
            historical_diagonal_variance[output_index] = diagonal[output_index]
            d0_run_ii_rows += 1
        elif row["process"] == "Z":
            primary = _primary_z_error(row)
            syst = float(transformed.get("systematic_error", 0.0))
            fraction = Z_NORMALIZATION_FRACTIONS[experiment]
            data[output_index] = float(transformed["value"])
            diagonal[output_index] = primary * primary + syst * syst
            normalization_fractions[output_index, normalization_column[experiment]] = fraction
            historical_diagonal_variance[output_index] = float(
                transformed["total_diagonal_error"]
            ) ** 2
            dyz_marginal_checks.append(
                abs(
                    diagonal[output_index]
                    + (fraction * data[output_index]) ** 2
                    - historical_diagonal_variance[output_index]
                )
            )
        else:  # pragma: no cover - fixed inventory
            raise ValueError(f"unsupported scored row: {row['source_id']}")

    arrays = {
        "data": data,
        "diagonal_variance": diagonal,
        "COMPASS_denominator_responses": compass_responses,
        "normalization_fraction_patterns": normalization_fractions,
        "historical_diagonal_variance": historical_diagonal_variance,
        "selected_raw_indices": selected_indices,
        "process_codes": process_codes,
    }

    invariants = {
        "all_arrays_finite": all(np.isfinite(array).all() for array in arrays.values()),
        "diagonal_variance_strictly_positive": bool((diagonal > 0).all()),
        "data_strictly_positive": bool((data > 0).all()),
        "one_COMPASS_response_per_COMPASS_row": bool(
            np.array_equal(
                np.count_nonzero(compass_responses, axis=1),
                np.asarray([1 if row["experiment"] == "COMPASS" else 0 for row in scored]),
            )
        ),
        "one_normalization_pattern_per_absolute_DY_Z_row": bool(
            np.array_equal(
                np.count_nonzero(normalization_fractions, axis=1),
                np.asarray(
                    [
                        1
                        if row["process"] in ("DY", "Z")
                        and row["experiment"] != "D0_RunII"
                        else 0
                        for row in scored
                    ]
                ),
            )
        ),
        "COMPASS_marginals_reproduce_published_propagation": bool(
            max(compass_marginal_checks, default=0.0) <= 2e-15
        ),
        "DY_Z_marginals_at_t0_equal_data_reproduce_legacy_diagonal": bool(
            max(dyz_marginal_checks, default=0.0) <= 2e-15
        ),
        "D0_RunII_uses_raw_normalized_shape_without_PV17_theory_factor": bool(
            all(
                normalization_fractions[i].sum() == 0
                and data[i] == float(row["raw"]["value"])
                for i, row in enumerate(scored)
                if row["experiment"] == "D0_RunII"
            )
        ),
    }
    if require_full_population:
        invariants.update(
            {
                "selected_raw_rows_equal_8283": len(selected) == 8283,
                "scored_observations_equal_8059": n == 8059,
                "COMPASS_groups_equal_224": len(compass_group_order) == 224,
                "experiment_counts_close": dict(experiment_counts)
                == EXPECTED_EXPERIMENT_COUNTS,
            }
        )
    if not all(invariants.values()):
        raise ValueError(f"PV17 metric-contract invariant failed: {invariants}")

    # The COMPASS columns have disjoint support.  This diagonal Gram therefore
    # diagnoses the Woodbury solve without assembling an 8,059-square matrix.
    whitened_compass_norm2 = np.sum(
        compass_responses * compass_responses / diagonal[:, None], axis=0
    )
    compass_gram_eigenvalues = 1.0 + whitened_compass_norm2
    compass_gram_min = float(compass_gram_eigenvalues.min()) if compass_gram_eigenvalues.size else 1.0
    compass_gram_max = float(compass_gram_eigenvalues.max()) if compass_gram_eigenvalues.size else 1.0

    metadata = {
        "scored_observations": n,
        "selected_raw_rows": len(selected),
        "experiment_counts": dict(sorted(experiment_counts.items())),
        "COMPASS_groups": compass_group_order,
        "normalization_groups": [
            {
                "id": group,
                "relative_fraction": (
                    DY_NORMALIZATION_FRACTIONS | Z_NORMALIZATION_FRACTIONS
                )[group],
                "response_rule": "relative_fraction_times_named_current_theory_t0",
            }
            for group in normalization_groups
        ],
        "invariants": invariants,
        "diagnostics": {
            "COMPASS_static_response_rank": len(compass_group_order),
            "normalization_response_rank_after_t0": len(normalization_groups),
            "COMPASS_woodbury_gram_eigenvalue_min": compass_gram_min,
            "COMPASS_woodbury_gram_eigenvalue_max": compass_gram_max,
            "COMPASS_woodbury_gram_condition": compass_gram_max / compass_gram_min,
            "max_COMPASS_marginal_variance_closure_abs": float(
                max(compass_marginal_checks, default=0.0)
            ),
            "max_DY_Z_data_reference_variance_closure_abs": float(
                max(dyz_marginal_checks, default=0.0)
            ),
            "D0_RunII_normalized_shape_rows": d0_run_ii_rows,
        },
    }
    return arrays, metadata


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--arrays-out", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args()

    rows, manifest_sha256 = read_manifest(args.manifest)
    arrays, metadata = build_metric_arrays(rows)
    args.arrays_out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.arrays_out, **arrays)
    array_receipts = {name: array_receipt(array) for name, array in arrays.items()}
    contract = {
        "schema": "pv17-current-method-metric-contract-v2",
        "status": "static_metric_built_D0II_normalized_denominator_and_t0_pending",
        "input_manifest_sha256": manifest_sha256,
        "counts": {
            "selected_raw_rows": metadata["selected_raw_rows"],
            "scored_observations": metadata["scored_observations"],
            "by_experiment": metadata["experiment_counts"],
            "COMPASS_denominator_constraints": len(metadata["COMPASS_groups"]),
        },
        "covariance": {
            "formula": "C_eff(t0)=diag(D)+U_COMPASS*U_COMPASS^T+(F_norm*t0[:,None])*(F_norm*t0[:,None])^T",
            "COMPASS": (
                "first-order Jacobian propagation from independent published raw stat/sys variances; "
                "shared lowest-PhT denominator retained as a within-spectrum response"
            ),
            "HERMES": "published stat and sys combined on the diagonal; no unavailable correlations invented",
            "DY_Z": (
                "published point errors on diagonal; absolute-spectrum normalization/luminosity as "
                "correlated t0 responses; normalized D0 Run-II is excluded from those responses"
            ),
            "t0_policy": (
                "a named current-theory prediction is fixed within a fit and may be updated only between "
                "versioned fits; measured data are not the production t0 reference"
            ),
            "theory_and_numerical_responses": "separate B1/B2 additions, never relabeled experimental covariance",
        },
        "observable_policy": {
            "COMPASS": "score numerator/lowest-PhT-theory ratios; denominator rows constrain the map but are not scored",
            "D0_RunII": (
                "score the experiment's raw normalized shape against a current-theory numerator/"
                "normalization-denominator quotient; exclude PV17's theory-derived sigma_Z=255.8 pb conversion"
            ),
            "PV17_fixed_Z_theory_normalization_factors": "excluded_from_current_theory_primary_fit",
            "reason": (
                "the factors 1.114/0.992/1.049/1.048 were corrections to PV17 theory and are not experimental data"
            ),
        },
        "normalization_groups": metadata["normalization_groups"],
        "diagnostics": metadata["diagnostics"],
        "invariants": metadata["invariants"],
        "arrays": array_receipts,
        "local_arrays": {
            "committed": False,
            "contains_third_party_measurements": True,
            "npz_sha256": sha256_bytes(args.arrays_out.read_bytes()),
        },
        "next_gate": (
            "Complete the source-corrected D0 Run-II normalized numerator/denominator contract, bind "
            "a feasible current-theory prediction as t0, then validate transformed predictions, "
            "covariance actions, and gradients."
        ),
    }
    contract["identity"] = sha256_bytes(canonical_json(contract).encode("utf-8"))
    write_json(args.receipt_out, contract)


if __name__ == "__main__":
    main()
