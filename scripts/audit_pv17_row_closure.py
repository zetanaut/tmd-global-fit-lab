#!/usr/bin/env python3
"""Reconstruct the PV17 baseline data population from a pinned legacy Git commit.

The historical data remain in their upstream repository.  This script reads
blobs with ``git show`` and can write a local, ignored JSONL manifest containing
the third-party row values.  Its public summary contains only counts, hashes,
and closure diagnostics.

This is a data audit, not an attempt to reproduce the PV17 NLL fit.  The
project's current matched theory and DNN will be used to fit the audited data.

The distinction between selected raw rows and the paper's point count matters:
PV17 divides every selected COMPASS spectrum by its lowest-PhT datum and excludes
that fixed denominator from the degrees of freedom.  The source tables therefore
produce 8,283 selected raw rows but 8,059 scored points.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence


PINNED_LEGACY_COMMIT = "7df66f4801151ce2384ca211422bdbfc70058832"
ARXIV_SOURCE_SHA256 = "1343dc940bbce30d6d5ec443f91f1f8d2181e4e6e4512006c28ea51a0efb2497"
SOURCE_ROOT = "resources/fortran_fitcode"

HERMES_EXPECTED = {
    ("proton", "kminus"): (336, 187),
    ("proton", "piminus"): (336, 190),
    ("proton", "piplus"): (336, 190),
    ("proton", "kplus"): (336, 189),
    ("deuteron", "kminus"): (336, 189),
    ("deuteron", "piminus"): (336, 190),
    ("deuteron", "piplus"): (336, 190),
    ("deuteron", "kplus"): (336, 189),
}

COMPASS_EXPECTED = {
    "piminus": (9311, 3239, 112, 3127),
    "piplus": (9313, 3237, 112, 3125),
}

DY_SPECS = (
    ("E288_400", 3, 177, 78, 0.25),
    ("E288_300", 4, 118, 45, 0.25),
    ("E288_200", 5, 89, 45, 0.25),
    ("E605", 6, 74, 35, 0.15),
)

Z_SPECS = (
    ("CDF_RunI", 7, 3, 50, 31, 0.039),
    ("D0_RunI", 8, 3, 26, 14, 0.044),
    ("CDF_RunII", 9, 4, 82, 37, 0.058),
    ("D0_RunII", 10, 4, 23, 8, 0.0),
)

COMPASS_X_BINS = (
    (0.0045, 0.006), (0.006, 0.008), (0.006, 0.008),
    (0.008, 0.012), (0.008, 0.012), (0.012, 0.018),
    (0.012, 0.018), (0.012, 0.018), (0.018, 0.025),
    (0.018, 0.025), (0.018, 0.025), (0.018, 0.025),
    (0.025, 0.035), (0.025, 0.04), (0.025, 0.04),
    (0.025, 0.04), (0.025, 0.04), (0.04, 0.05),
    (0.04, 0.07), (0.04, 0.07), (0.04, 0.07),
    (0.07, 0.12), (0.07, 0.12),
)
COMPASS_Q2_BINS = (
    (1.0, 1.25), (1.0, 1.3), (1.3, 1.7), (1.0, 1.5),
    (1.5, 2.1), (1.0, 1.5), (1.5, 2.5), (2.5, 3.5),
    (1.0, 1.5), (1.5, 2.5), (2.5, 3.5), (3.5, 5.0),
    (1.0, 1.2), (1.2, 1.5), (1.5, 2.5), (2.5, 3.5),
    (3.5, 6.0), (1.5, 2.5), (2.5, 3.5), (3.5, 6.0),
    (6.0, 10.0), (3.5, 6.0), (6.0, 10.0),
)
COMPASS_Z_BINS = (
    (0.20, 0.25), (0.25, 0.30), (0.30, 0.35), (0.35, 0.40),
    (0.40, 0.50), (0.50, 0.60), (0.60, 0.70), (0.70, 0.80),
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def git_blob(repository: Path, commit: str, relative_path: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repository), "show", f"{commit}:{relative_path}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode:
        message = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"cannot read {relative_path!r} at {commit}: {message}")
    return completed.stdout


def verify_commit(repository: Path, commit: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "--verify", f"{commit}^{{commit}}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode:
        raise ValueError(f"legacy commit is unavailable in {repository}: {commit}")
    resolved = completed.stdout.strip()
    if resolved != commit:
        raise ValueError(f"legacy commit resolved unexpectedly: {resolved} != {commit}")
    return resolved


def numeric_rows(payload: bytes, *, skip_lines: int, fields: int) -> list[tuple[int, list[float]]]:
    rows: list[tuple[int, list[float]]] = []
    text = payload.decode("utf-8", errors="strict")
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line_number <= skip_lines:
            continue
        pieces = line.split()
        if len(pieces) != fields:
            continue
        try:
            values = [float(piece.replace("D", "E").replace("d", "e")) for piece in pieces]
        except ValueError:
            continue
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"nonfinite source value on line {line_number}")
        rows.append((line_number, values))
    return rows


def sidis_cut_checks(q2: float, z: float, pht: float, statistical_error: float) -> dict[str, bool]:
    q = math.sqrt(q2) if q2 >= 0.0 else math.nan
    return {
        "statistical_error_gt_0": statistical_error > 0.0,
        "Q2_gt_1p4_GeV2": q2 > 1.4,
        "z_gt_0p2": z > 0.2,
        "z_lt_0p74": z < 0.74,
        "PhT_lt_0p2Q_plus_0p5_GeV": pht < 0.2 * q + 0.5,
        "PhT_lt_0p7Qz_plus_0p5_GeV": pht < 0.7 * q * z + 0.5,
    }


def dy_cut_checks(experiment_index: int, mass: float, qt: float) -> dict[str, bool]:
    if experiment_index == 3:
        mass_window = (4.0 < mass < 9.0) or (11.0 < mass < 14.0)
    elif experiment_index in (4, 5):
        mass_window = 4.0 < mass < 9.0
    elif experiment_index == 6:
        mass_window = (7.0 < mass < 9.0) or (10.0 < mass < 12.0)
    else:  # pragma: no cover - guarded by the fixed experiment inventory
        raise ValueError(f"unexpected DY experiment index: {experiment_index}")
    return {
        "historical_mass_window": mass_window,
        "qT_le_0p2Q_plus_0p5_GeV": qt <= 0.2 * mass + 0.5,
    }


def strict_bin_index(value: float, bins: Sequence[tuple[float, float]]) -> int | None:
    return next((index for index, (low, high) in enumerate(bins) if low < value < high), None)


def compass_bin_key(row: dict[str, Any]) -> tuple[int, int, int]:
    values = row["raw"]
    x_index = strict_bin_index(values["x"], COMPASS_X_BINS)
    q2_index = strict_bin_index(values["Q2_GeV2"], COMPASS_Q2_BINS)
    z_index = strict_bin_index(values["z"], COMPASS_Z_BINS)
    if None in (x_index, q2_index, z_index):
        raise ValueError(f"selected COMPASS row has no legacy bin: {row['source_id']}")
    return int(x_index), int(q2_index), int(z_index)


def apply_compass_normalization(rows: list[dict[str, Any]], hadron: str) -> int:
    selected = [row for row in rows if row["selected_by_kinematic_cuts"]]
    exact_groups: dict[tuple[float, float, float], list[dict[str, Any]]] = {}
    binned_groups: dict[tuple[int, int, int], tuple[float, float, float]] = {}
    for row in selected:
        raw = row["raw"]
        exact_key = (raw["x"], raw["z"], raw["Q2_GeV2"])
        exact_groups.setdefault(exact_key, []).append(row)
        bin_key = compass_bin_key(row)
        previous = binned_groups.setdefault(bin_key, exact_key)
        if previous != exact_key:
            raise ValueError(f"legacy bin merges distinct COMPASS spectra: {bin_key}")

    for group_number, group_rows in enumerate(exact_groups.values(), start=1):
        denominator = min(group_rows, key=lambda item: item["raw"]["PhT_GeV"])
        if denominator is not group_rows[0]:
            raise ValueError(f"lowest-PhT COMPASS row is not first: {denominator['source_id']}")
        denominator_raw = denominator["raw"]
        group_id = f"COMPASS_{hadron}_spectrum_{group_number:03d}"
        for row in group_rows:
            raw = row["raw"]
            ratio = raw["value"] / denominator_raw["value"]
            statistical = ratio * math.sqrt(
                (raw["statistical_error"] / raw["value"]) ** 2
                + (denominator_raw["statistical_error"] / denominator_raw["value"]) ** 2
            )
            systematic = ratio * math.sqrt(
                (raw["systematic_error"] / raw["value"]) ** 2
                + (denominator_raw["systematic_error"] / denominator_raw["value"]) ** 2
            )
            row["normalization"] = {
                "group": group_id,
                "denominator_source_id": denominator["source_id"],
                "is_fixed_denominator": row is denominator,
                "rule": "divide_data_and_theory_by_lowest_PhT_row",
            }
            row["transformed"] = {
                "value": ratio,
                "statistical_error": statistical,
                "systematic_error": systematic,
                "fragmentation_function_error": "prediction_dependent_pending_H1",
            }
            row["contributes_to_published_point_count"] = row is not denominator
    if len(exact_groups) != len(binned_groups):
        raise ValueError("exact and legacy-binned COMPASS group counts disagree")
    return len(exact_groups)


def sidis_file_specs() -> list[tuple[str, str, str, str]]:
    """Return the historical Fortran traversal order with the PV17 COMPASS tables."""
    specs: list[tuple[str, str, str, str]] = []
    for target in ("proton", "deuteron"):
        for hadron in ("kminus", "piminus", "piplus", "kplus"):
            specs.append(
                (
                    "HERMES",
                    target,
                    hadron,
                    f"{SOURCE_ROOT}/data/hermes.{target}.zxpt-3D.vmsub.mults_{hadron}.list",
                )
            )
            if target == "deuteron" and hadron in ("piminus", "piplus"):
                specs.append(
                    (
                        "COMPASS",
                        target,
                        hadron,
                        f"{SOURCE_ROOT}/data/Compass_Multiplicities_{hadron}.dat",
                    )
                )
    return specs


def add_source_receipt(
    receipts: list[dict[str, Any]], path: str, payload: bytes, candidate_rows: int
) -> None:
    receipts.append(
        {
            "path": path,
            "bytes": len(payload),
            "sha256": sha256_bytes(payload),
            "candidate_numeric_rows": candidate_rows,
        }
    )


def build_sidis_rows(
    repository: Path, commit: str, receipts: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    manifest: list[dict[str, Any]] = []
    groups_by_hadron: dict[str, int] = {}
    for experiment, target, hadron, path in sidis_file_specs():
        payload = git_blob(repository, commit, path)
        parsed = numeric_rows(payload, skip_lines=19, fields=8)
        add_source_receipt(receipts, path, payload, len(parsed))
        file_rows: list[dict[str, Any]] = []
        for source_line, values in parsed:
            source_row, value, statistical, systematic, q2, x, z, pht = values
            checks = sidis_cut_checks(q2, z, pht, statistical)
            selected = all(checks.values())
            row: dict[str, Any] = {
                "source_id": f"git:{commit}:{path}:line{source_line}",
                "source_path": path,
                "source_line": source_line,
                "source_table_row": int(source_row),
                "process": "SIDIS",
                "experiment": experiment,
                "target": target,
                "detected_hadron": hadron,
                "observable": "normalized_multiplicity" if experiment == "COMPASS" else "multiplicity",
                "raw": {
                    "value": value,
                    "statistical_error": statistical,
                    "systematic_error": systematic,
                    "Q2_GeV2": q2,
                    "x": x,
                    "z": z,
                    "PhT_GeV": pht,
                },
                "cut_checks": checks,
                "selected_by_kinematic_cuts": selected,
                "contributes_to_published_point_count": selected,
            }
            if selected and experiment == "HERMES":
                row["normalization"] = {"rule": "identity", "group": None}
                row["transformed"] = {
                    "value": value,
                    "statistical_error": statistical,
                    "systematic_error": systematic,
                    "fragmentation_function_error": "prediction_dependent_pending_H1",
                }
            file_rows.append(row)

        selected_count = sum(row["selected_by_kinematic_cuts"] for row in file_rows)
        if experiment == "HERMES":
            expected_candidates, expected_selected = HERMES_EXPECTED[(target, hadron)]
            if (len(parsed), selected_count) != (expected_candidates, expected_selected):
                raise ValueError(
                    f"HERMES count mismatch for {target}/{hadron}: "
                    f"{(len(parsed), selected_count)} != {(expected_candidates, expected_selected)}"
                )
        else:
            expected_candidates, expected_selected, expected_groups, expected_scored = (
                COMPASS_EXPECTED[hadron]
            )
            groups = apply_compass_normalization(file_rows, hadron)
            scored = sum(row["contributes_to_published_point_count"] for row in file_rows)
            if (len(parsed), selected_count, groups, scored) != (
                expected_candidates, expected_selected, expected_groups, expected_scored
            ):
                raise ValueError(
                    f"COMPASS count mismatch for {hadron}: "
                    f"{(len(parsed), selected_count, groups, scored)}"
                )
            groups_by_hadron[hadron] = groups
        manifest.extend(file_rows)
    return manifest, groups_by_hadron


def build_dy_rows(
    repository: Path, commit: str, receipts: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    for experiment, experiment_index, expected_candidates, expected_selected, relative_systematic in DY_SPECS:
        path = f"{SOURCE_ROOT}/data/DY.{experiment}.list"
        payload = git_blob(repository, commit, path)
        parsed = numeric_rows(payload, skip_lines=15, fields=4)
        add_source_receipt(receipts, path, payload, len(parsed))
        file_rows: list[dict[str, Any]] = []
        for source_line, values in parsed:
            mass, qt, value, statistical = values
            checks = dy_cut_checks(experiment_index, mass, qt)
            selected = all(checks.values())
            systematic = relative_systematic * value
            row: dict[str, Any] = {
                "source_id": f"git:{commit}:{path}:line{source_line}",
                "source_path": path,
                "source_line": source_line,
                "process": "DY",
                "experiment": experiment,
                "observable": "E_d3sigma_dp3_cm2_per_GeV2_per_nucleon",
                "raw": {
                    "value": value,
                    "statistical_error": statistical,
                    "Q_GeV": mass,
                    "qT_GeV": qt,
                },
                "cut_checks": checks,
                "selected_by_kinematic_cuts": selected,
                "contributes_to_published_point_count": selected,
            }
            if selected:
                row["normalization"] = {"rule": "identity", "group": None}
                row["transformed"] = {
                    "value": value,
                    "statistical_error": statistical,
                    "systematic_error": systematic,
                    "systematic_relative_fraction": relative_systematic,
                    "total_diagonal_error": math.hypot(statistical, systematic),
                }
            file_rows.append(row)
        selected_count = sum(row["selected_by_kinematic_cuts"] for row in file_rows)
        if (len(parsed), selected_count) != (expected_candidates, expected_selected):
            raise ValueError(
                f"DY count mismatch for {experiment}: {(len(parsed), selected_count)} "
                f"!= {(expected_candidates, expected_selected)}"
            )
        manifest.extend(file_rows)
    return manifest


def build_z_rows(
    repository: Path, commit: str, receipts: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    for (
        experiment, experiment_index, fields, expected_candidates, expected_selected, luminosity_fraction
    ) in Z_SPECS:
        path = f"{SOURCE_ROOT}/data/DY.{experiment}.list"
        payload = git_blob(repository, commit, path)
        parsed = numeric_rows(payload, skip_lines=20, fields=fields)
        add_source_receipt(receipts, path, payload, len(parsed))
        file_rows: list[dict[str, Any]] = []
        for source_line, values in parsed:
            qt, value, table_error = values[:3]
            systematic = values[3] if fields == 4 else 0.0
            checks = {"qT_le_18p7_GeV": qt <= 18.7}
            selected = all(checks.values())
            transformed_value = value
            transformed_statistical = table_error
            transformed_systematic = systematic
            total_error = math.sqrt(
                table_error**2 + systematic**2 + (luminosity_fraction * value) ** 2
            )
            transformation: dict[str, Any] = {
                "value": transformed_value,
                "statistical_or_published_combined_error": transformed_statistical,
                "systematic_error": transformed_systematic,
                "luminosity_relative_fraction": luminosity_fraction,
                "total_diagonal_error": total_error,
            }
            if experiment_index == 10:
                sigma_z, sigma_z_error = 255.8, 16.7
                transformed_value = value * sigma_z
                raw_combined = math.hypot(table_error, systematic)
                total_error = math.sqrt((value * sigma_z_error) ** 2 + (sigma_z * raw_combined) ** 2)
                transformation = {
                    "value": transformed_value,
                    "statistical_error": table_error * sigma_z,
                    "systematic_error": systematic * sigma_z,
                    "integrated_sigma_Z_pb": sigma_z,
                    "integrated_sigma_Z_error_pb": sigma_z_error,
                    "total_diagonal_error": total_error,
                    "rule": "convert_(1/sigma_Z)_dsigma_dqT_to_dsigma_dqT",
                }
            row: dict[str, Any] = {
                "source_id": f"git:{commit}:{path}:line{source_line}",
                "source_path": path,
                "source_line": source_line,
                "process": "Z",
                "experiment": experiment,
                "observable": (
                    "normalized_dsigma_dqT" if experiment_index == 10 else "dsigma_dqT_pb_per_GeV"
                ),
                "raw": {
                    "value": value,
                    "statistical_or_published_combined_error": table_error,
                    "systematic_error": systematic,
                    "Q_GeV": 91.1876,
                    "qT_GeV": qt,
                },
                "cut_checks": checks,
                "selected_by_kinematic_cuts": selected,
                "contributes_to_published_point_count": selected,
            }
            if selected:
                row["normalization"] = {
                    "rule": "fixed_theory_normalization_factor",
                    "factor": {7: 1.114, 8: 0.992, 9: 1.049, 10: 1.048}[experiment_index],
                    "group": None,
                }
                row["transformed"] = transformation
            file_rows.append(row)
        selected_count = sum(row["selected_by_kinematic_cuts"] for row in file_rows)
        if (len(parsed), selected_count) != (expected_candidates, expected_selected):
            raise ValueError(
                f"Z count mismatch for {experiment}: {(len(parsed), selected_count)} "
                f"!= {(expected_candidates, expected_selected)}"
            )
        manifest.extend(file_rows)
    return manifest


def source_bundle_digest(receipts: Iterable[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for receipt in receipts:
        digest.update(receipt["path"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(receipt["sha256"].encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def bind_manifest_indices(rows: list[dict[str, Any]]) -> tuple[str, list[str]]:
    digest = hashlib.sha256()
    serialized: list[str] = []
    selected_index = 0
    scored_index = 0
    for candidate_index, row in enumerate(rows, start=1):
        row["candidate_index"] = candidate_index
        if row["selected_by_kinematic_cuts"]:
            selected_index += 1
            row["selected_index"] = selected_index
        else:
            row["selected_index"] = None
        if row["contributes_to_published_point_count"]:
            scored_index += 1
            row["published_point_index"] = scored_index
        else:
            row["published_point_index"] = None
        line = canonical_json(row)
        serialized.append(line)
        digest.update(line.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest(), serialized


def summarize(
    repository: Path,
    commit: str,
    rows: list[dict[str, Any]],
    receipts: list[dict[str, Any]],
    groups_by_hadron: dict[str, int],
    manifest_sha256: str,
) -> dict[str, Any]:
    selected = [row for row in rows if row["selected_by_kinematic_cuts"]]
    scored = [row for row in rows if row["contributes_to_published_point_count"]]
    selected_process = Counter(row["process"] for row in selected)
    scored_process = Counter(row["process"] for row in scored)
    scored_experiment = Counter(row["experiment"] for row in scored)
    constraints = sum(
        row.get("normalization", {}).get("is_fixed_denominator", False) for row in selected
    )
    observation_keys = []
    for row in selected:
        raw = row["raw"]
        if row["process"] == "SIDIS":
            key = (
                row["experiment"], row["target"], row["detected_hadron"],
                raw["Q2_GeV2"], raw["x"], raw["z"], raw["PhT_GeV"],
            )
        else:
            key = (row["process"], row["experiment"], raw["Q_GeV"], raw["qT_GeV"])
        observation_keys.append(key)
    main_errors = [
        row["raw"].get(
            "statistical_error", row["raw"].get("statistical_or_published_combined_error")
        )
        for row in selected
    ]
    compass_group_sizes = Counter(
        row["normalization"]["group"] for row in selected if row["experiment"] == "COMPASS"
    )
    invariants = {
        "selected_raw_rows_equal_8283": len(selected) == 8283,
        "selected_SIDIS_rows_equal_7990": selected_process == {"SIDIS": 7990, "DY": 203, "Z": 90},
        "COMPASS_fixed_denominators_equal_224": constraints == 224,
        "published_effective_points_equal_8059": len(scored) == 8059,
        "published_process_counts_close": scored_process == {"SIDIS": 7766, "DY": 203, "Z": 90},
        "published_experiment_counts_close": scored_experiment
        == {"HERMES": 1514, "COMPASS": 6252, "E288_400": 78, "E288_300": 45,
            "E288_200": 45, "E605": 35, "CDF_RunI": 31, "D0_RunI": 14,
            "CDF_RunII": 37, "D0_RunII": 8},
        "selected_source_ids_unique": len({row["source_id"] for row in selected}) == len(selected),
        "selected_observation_keys_unique": len(set(observation_keys)) == len(observation_keys),
        "selected_central_values_positive": all(row["raw"]["value"] > 0.0 for row in selected),
        "selected_primary_errors_positive": all(error is not None and error > 0.0 for error in main_errors),
        "COMPASS_group_sizes_between_19_and_44": (
            min(compass_group_sizes.values()) == 19 and max(compass_group_sizes.values()) == 44
        ),
    }
    if not all(invariants.values()):
        raise ValueError(f"PV17 row-closure invariant failed: {invariants}")

    key_paths = (
        f"{SOURCE_ROOT}/input_choices.h",
        f"{SOURCE_ROOT}/reading.f",
        f"{SOURCE_ROOT}/ref.txt",
    )
    key_receipts = []
    for path in key_paths:
        payload = git_blob(repository, commit, path)
        key_receipts.append({"path": path, "bytes": len(payload), "sha256": sha256_bytes(payload)})

    return {
        "schema_version": "pv17-row-closure-v1",
        "generated_from": {
            "paper": "arXiv:1703.10157",
            "paper_source_sha256": ARXIV_SOURCE_SHA256,
            "legacy_repository": "https://github.com/MapCollaboration/NangaParbat-Legacy",
            "legacy_local_path_recorded": False,
            "legacy_commit": commit,
        },
        "verdict": {
            "data_population_and_COMPASS_normalization_closure": "passed",
            "historical_PV17_fit_reproduction": "out_of_scope",
            "current_matched_theory_operator": "not_built",
            "reason": (
                "The exact PV17 data population is the baseline input. The project will fit it with "
                "its current N3LL matched theory, likelihood, and DNN rather than reproduce PV17 NLL."
            ),
        },
        "counts": {
            "candidate_numeric_rows": len(rows),
            "selected_raw_rows_before_COMPASS_fixed_constraints": len(selected),
            "selected_raw_rows_by_process": dict(sorted(selected_process.items())),
            "COMPASS_normalization_spectra_by_hadron": dict(sorted(groups_by_hadron.items())),
            "COMPASS_fixed_denominator_constraints": constraints,
            "published_effective_points": len(scored),
            "published_effective_points_by_process": dict(sorted(scored_process.items())),
            "published_effective_points_by_experiment": dict(sorted(scored_experiment.items())),
            "historical_PV17_free_parameters": 11,
            "historical_PV17_nominal_degrees_of_freedom": len(scored) - 11,
            "COMPASS_normalization_group_size_min": min(compass_group_sizes.values()),
            "COMPASS_normalization_group_size_max": max(compass_group_sizes.values()),
        },
        "interpretation": {
            "8059_is_not_the_selected_raw_table_row_count": True,
            "accounting_equation": "8283 selected raw rows - 224 COMPASS fixed denominators = 8059 points",
            "SIDIS_equation": "7990 selected raw SIDIS rows - 224 COMPASS fixed denominators = 7766 points",
            "COMPASS_equation": "6476 selected raw COMPASS rows - 224 spectra = 6252 points",
        },
        "invariants": invariants,
        "source_data_receipts": {
            "ordered_file_count": len(receipts),
            "ordered_path_and_content_digest_sha256": source_bundle_digest(receipts),
            "files": receipts,
        },
        "local_manifest": {
            "schema": "canonical JSONL, one candidate numeric source row per line",
            "rows": len(rows),
            "sha256": manifest_sha256,
            "contains_third_party_measurements": True,
            "redistribute_or_commit": False,
        },
        "historical_fit_configuration_context_not_a_gate": {
            "key_file_receipts": key_receipts,
            "paper_matching_final_configuration_identified": False,
            "full_8059_historical_prediction_receipt_identified": False,
            "required_for_current_data_baseline": False,
            "known_mismatches": [
                "checked-in input_choices.h selects MMHT2014 rather than published GJR08FFnloE",
                "checked-in input_choices.h disables SIDIS and DY and enables Z only",
                "checked-in reading.f selects later Compass17 tables rather than PV17 Compass_Multiplicities tables",
                "checked-in ref.txt has the correct effective count but chi2/dof 477.97623960906037",
            ],
        },
        "next_gate": (
            "Freeze the current N3LL matched-theory, collinear-input, covariance, and COMPASS-ratio "
            "contracts for these rows; then construct and independently validate the new operator."
        ),
    }


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-repo", type=Path, required=True)
    parser.add_argument("--legacy-commit", default=PINNED_LEGACY_COMMIT)
    parser.add_argument("--summary-out", type=Path)
    parser.add_argument("--manifest-out", type=Path)
    args = parser.parse_args()

    repository = args.legacy_repo.resolve()
    commit = verify_commit(repository, args.legacy_commit)
    receipts: list[dict[str, Any]] = []
    sidis_rows, groups_by_hadron = build_sidis_rows(repository, commit, receipts)
    rows = sidis_rows + build_dy_rows(repository, commit, receipts) + build_z_rows(
        repository, commit, receipts
    )
    manifest_sha256, serialized_rows = bind_manifest_indices(rows)
    summary = summarize(
        repository, commit, rows, receipts, groups_by_hadron, manifest_sha256
    )

    summary_text = json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.summary_out is not None:
        write_text(args.summary_out, summary_text)
    else:
        print(summary_text, end="")
    if args.manifest_out is not None:
        write_text(args.manifest_out, "\n".join(serialized_rows) + "\n")


if __name__ == "__main__":
    main()
