#!/usr/bin/env python3
"""Audit PV17 SIDIS point kinematics against the current regional theory path.

This is a read-only feasibility audit.  It does not import or evaluate the
native theory service, build operators, or generate predictions.  The audit
also records why the older fixed-nf common service is not an acceptable
shortcut for this population.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


REGIONAL_DOMAIN = {
    "x_min": 0.003,
    "z_min": 0.2,
    "Q_min_GeV": 1.05,
    "Q_max_GeV": 10.0,
}
OLDER_FIXED_NF_DOMAIN = {
    "x_min": 0.01,
    "z_min": 0.2,
    "Q_min_GeV": 1.55,
    "Q_max_GeV": 4.5,
}
TRANSITION = {"full_TMD_through_qT_over_Q": 0.15, "FO_only_from_qT_over_Q": 0.30}
BEAM_CONVENTIONS = {
    "HERMES": {
        "beam_energy_GeV": 27.6,
        "target_mass_GeV": 0.93827208816,
        "S_lN_GeV2": 51.792619266432,
        "y_range": [0.1, 0.85],
        "W_min_GeV": math.sqrt(10.0),
        "target_mass_semantics": "current per-nucleon proton-mass convention",
    },
    "COMPASS": {
        "beam_energy_GeV": 160.0,
        "target_mass_GeV": 0.93891875434,
        "S_lN_GeV2": 300.45400138879995,
        "y_range": [0.1, 0.9],
        "W_min_GeV": 5.0,
        "target_mass_semantics": "current free-proton/neutron arithmetic mean per nucleon",
    },
}
SOURCE_FILES = (
    "work/regional_matching/service.py",
    "work/regional_matching/panel.py",
    "work/regional_matching/w.py",
    "work/regional_matching/coupling.py",
    "work/regional_matching/pilot.py",
    "work/full_sample_sidis/builder.py",
    "src/bttmd_foundation/sidis_uv_subtraction.py",
    "src/bttmd_foundation/sidis_distribution_action.py",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def region(row: dict[str, Any]) -> str:
    raw = row["raw"]
    ratio = float(raw["PhT_GeV"]) / (
        float(raw["z"]) * math.sqrt(float(raw["Q2_GeV2"]))
    )
    if ratio <= TRANSITION["full_TMD_through_qT_over_Q"]:
        return "full_additive"
    if ratio < TRANSITION["FO_only_from_qT_over_Q"]:
        return "transition"
    return "FO_only"


def domain_failures(row: dict[str, Any], domain: dict[str, float]) -> tuple[str, ...]:
    raw = row["raw"]
    x, z = float(raw["x"]), float(raw["z"])
    Q = math.sqrt(float(raw["Q2_GeV2"]))
    failures = []
    if x < domain["x_min"]:
        failures.append("x_below_min")
    if z < domain["z_min"]:
        failures.append("z_below_min")
    if Q < domain["Q_min_GeV"]:
        failures.append("Q_below_min")
    if Q > domain["Q_max_GeV"]:
        failures.append("Q_above_max")
    return tuple(failures)


def point_kinematics(row: dict[str, Any]) -> dict[str, float]:
    raw = row["raw"]
    x, z = float(raw["x"]), float(raw["z"])
    Q2, PhT = float(raw["Q2_GeV2"]), float(raw["PhT_GeV"])
    beam = BEAM_CONVENTIONS[row["experiment"]]
    y = Q2 / (x * beam["S_lN_GeV2"])
    W2 = beam["target_mass_GeV"] ** 2 + Q2 * (1 / x - 1)
    qT2 = (PhT / z) ** 2
    recoil_limit = Q2 * (1 - x) * (1 - z) / (x * z)
    return {
        "x": x,
        "z": z,
        "Q_GeV": math.sqrt(Q2),
        "PhT_GeV": PhT,
        "qT_over_Q": math.sqrt(qT2 / Q2),
        "y": y,
        "W_GeV": math.sqrt(W2),
        "qT2_GeV2": qT2,
        "finite_recoil_qT2_limit_GeV2": recoil_limit,
    }


def _count_status(rows: Iterable[dict[str, Any]], domain: dict[str, float]) -> dict[str, Any]:
    rows = list(rows)
    combinations: Counter[str] = Counter()
    violations: Counter[str] = Counter()
    supported = 0
    for row in rows:
        failures = domain_failures(row, domain)
        if not failures:
            supported += 1
            combinations["inside"] += 1
        else:
            combinations["+".join(failures)] += 1
            violations.update(failures)
    return {
        "rows": len(rows),
        "inside": supported,
        "outside": len(rows) - supported,
        "individual_violation_counts": dict(sorted(violations.items())),
        "exclusive_failure_combinations": dict(sorted(combinations.items())),
    }


def audit_domain(rows: Iterable[dict[str, Any]], *, require_full_population: bool = True) -> dict[str, Any]:
    sidis = [
        row
        for row in rows
        if row.get("selected_by_kinematic_cuts") and row.get("process") == "SIDIS"
    ]
    by_source = {row["source_id"]: row for row in sidis}
    if len(by_source) != len(sidis):
        raise ValueError("selected SIDIS source ids are not unique")

    kinematics = [point_kinematics(row) for row in sidis]
    regional = _count_status(sidis, REGIONAL_DOMAIN)
    older = _count_status(sidis, OLDER_FIXED_NF_DOMAIN)
    experiment_counts = Counter(row["experiment"] for row in sidis)
    target_counts = Counter(row["target"] for row in sidis)
    hadron_counts = Counter(row["detected_hadron"] for row in sidis)
    role_counts = Counter(region(row) for row in sidis)

    denominators = [
        row
        for row in sidis
        if row.get("normalization", {}).get("is_fixed_denominator")
    ]
    scored = [row for row in sidis if row["contributes_to_published_point_count"]]
    dnn_coupling: Counter[str] = Counter()
    for row in scored:
        if row["experiment"] == "HERMES":
            coupled = region(row) != "FO_only"
        else:
            denominator_id = row["normalization"]["denominator_source_id"]
            if denominator_id not in by_source:
                raise ValueError(f"missing COMPASS denominator: {denominator_id}")
            coupled = region(row) != "FO_only" or region(by_source[denominator_id]) != "FO_only"
        dnn_coupling["DNN_coupled"] += int(coupled)
        dnn_coupling["FO_only"] += int(not coupled)

    by_experiment = {}
    for experiment in sorted(experiment_counts):
        subset = [row for row in sidis if row["experiment"] == experiment]
        by_experiment[experiment] = {
            "raw_rows": len(subset),
            "scored_rows": sum(row["contributes_to_published_point_count"] for row in subset),
            "matching_roles": dict(sorted(Counter(region(row) for row in subset).items())),
            "regional_domain": _count_status(subset, REGIONAL_DOMAIN),
            "older_fixed_nf_domain": _count_status(subset, OLDER_FIXED_NF_DOMAIN),
        }

    invariants = {
        "selected_SIDIS_raw_rows_equal_7990": len(sidis) == 7990,
        "scored_SIDIS_rows_equal_7766": len(scored) == 7766,
        "COMPASS_denominators_equal_224": len(denominators) == 224,
        "all_rows_inside_current_regional_fraction_and_scale_domain": regional["outside"] == 0,
        "all_rows_inside_positive_recoil_partonic_support": all(
            item["qT2_GeV2"] < item["finite_recoil_qT2_limit_GeV2"]
            for item in kinematics
        ),
        "all_average_points_inside_current_experiment_y_and_W_contract": all(
            BEAM_CONVENTIONS[row["experiment"]]["y_range"][0]
            <= item["y"]
            <= BEAM_CONVENTIONS[row["experiment"]]["y_range"][1]
            and item["W_GeV"] >= BEAM_CONVENTIONS[row["experiment"]]["W_min_GeV"]
            for row, item in zip(sidis, kinematics)
        ),
        "older_fixed_nf_shortcut_rejects_2505_rows": older["outside"] == 2505,
        "matching_roles_sum_to_raw_rows": sum(role_counts.values()) == len(sidis),
        "DNN_coupling_classes_sum_to_scored_SIDIS": sum(dnn_coupling.values()) == len(scored),
    }
    if require_full_population and not all(invariants.values()):
        raise ValueError(f"PV17 SIDIS domain invariant failed: {invariants}")

    extrema = {
        name: [min(item[name] for item in kinematics), max(item[name] for item in kinematics)]
        for name in ("x", "z", "Q_GeV", "PhT_GeV", "qT_over_Q", "y", "W_GeV")
    }
    return {
        "counts": {
            "selected_SIDIS_raw_rows": len(sidis),
            "scored_SIDIS_observations": len(scored),
            "COMPASS_fixed_denominators": len(denominators),
            "by_experiment": dict(sorted(experiment_counts.items())),
            "by_target": dict(sorted(target_counts.items())),
            "by_hadron": dict(sorted(hadron_counts.items())),
        },
        "kinematic_extrema": extrema,
        "current_regional_domain": {"contract": REGIONAL_DOMAIN, **regional},
        "older_fixed_nf_shortcut": {"contract": OLDER_FIXED_NF_DOMAIN, **older},
        "matching_roles_raw_rows": dict(sorted(role_counts.items())),
        "scored_SIDIS_DNN_coupling_after_COMPASS_ratio_map": dict(sorted(dnn_coupling.items())),
        "by_experiment": by_experiment,
        "beam_conventions": BEAM_CONVENTIONS,
        "invariants": invariants,
    }


def source_contract(foundation_root: Path) -> dict[str, Any]:
    root = foundation_root.resolve()
    result = {}
    payloads = {}
    for relative in SOURCE_FILES:
        path = root / relative
        payload = path.read_bytes()
        payloads[relative] = payload.decode("utf-8")
        result[relative] = sha256_bytes(payload)

    required_fragments = {
        "work/regional_matching/service.py": (
            "mu_min_GeV: float = 1.05",
            "mu_max_GeV: float = 10.",
            "pdf_xmin: float = .003",
            "ff_zmin: float = .2",
            "heavy_threshold_complete = False",
        ),
        "work/regional_matching/pilot.py": (
            "W='unprimed N3LL massless reference'",
            "recoil='NLO'",
            "DIS='NLO'",
        ),
        "work/full_sample_sidis/builder.py": (
            "matching='fW+FO-fASY; f inside qT2 integral'",
            "heavy_threshold_complete=False",
        ),
        "src/bttmd_foundation/sidis_uv_subtraction.py": ("def subtraction_density",),
        "src/bttmd_foundation/sidis_distribution_action.py": ("def source_pht2_density",),
    }
    missing = {
        path: [fragment for fragment in fragments if fragment not in payloads[path]]
        for path, fragments in required_fragments.items()
    }
    missing = {path: fragments for path, fragments in missing.items() if fragments}
    if missing:
        raise ValueError(f"current regional theory source contract changed: {missing}")
    return {
        "files": result,
        "required_fragments_verified": True,
        "native_service_imported": False,
        "operator_or_prediction_evaluated": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--foundation-root", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args()

    manifest_payload = args.manifest.read_bytes()
    rows = [json.loads(line) for line in manifest_payload.splitlines() if line.strip()]
    receipt = {
        "schema": "pv17-current-regional-sidis-domain-v1",
        "status": "domain_closed_point_operator_pilot_open",
        "source_receipts": {
            "pv17_manifest_sha256": sha256_bytes(manifest_payload),
            "current_regional_theory": source_contract(args.foundation_root),
        },
        **audit_domain(rows),
        "interpretation": {
            "domain_result": (
                "All 7990 selected raw SIDIS points are inside the declared current regional "
                "fraction, scale, experiment-y/W, and finite-recoil support."
            ),
            "forbidden_shortcut": (
                "Do not use the older fixed-nf common service: it would reject 2505 rows and "
                "cannot cross the low-Q flavor thresholds."
            ),
            "theory_scope": (
                "The reusable current path is an unprimed N3LL massless W with NLO SIDIS "
                "positive recoil and an NLO inclusive-DIS denominator.  It is explicitly "
                "heavy-threshold-incomplete and production_authorized=false; do not label the "
                "combined SIDIS observable uniformly N3LL+NNLO."
            ),
            "point_operator": (
                "Existing primitives expose positive-qT ASY density and the PhT2 Jacobian, "
                "but the present campaign builder integrates source bins.  A dedicated average-"
                "point operator and bin-shrinkage/reintegration validation remain required."
            ),
        },
        "next_gate": (
            "Implement and validate one current-regional average-point operator for HERMES and "
            "one complete COMPASS numerator/denominator spectrum before bulk construction."
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
