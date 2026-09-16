#!/usr/bin/env python3
"""Audit the full COMPASS HEPData release and rescore a saved endpoint.

This is a diagnostic, not a likelihood migration.  It deliberately keeps two
questions separate:

1. What kinematic and nominal information roles do all public COMPASS rows have?
2. How would fixed theory-error covariance choices change the score of the
   already-computed 2,290-row endpoint?

The new public rows are never assigned predictions.  A full-data fit still
requires exact operators, covariance decisions, and validation for those rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from scipy.linalg import cho_factor, cho_solve


NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
BIN_RE = re.compile(rf"BIN\s*=\s*({NUMBER})\s+TO\s+({NUMBER})", re.IGNORECASE)
TABLE_RE = re.compile(r"data(\d+)\.yaml$")
THRESHOLDS = (0.10, 0.15, 0.20, 0.25, 0.30, 0.34)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_receipt(path: Path) -> dict[str, Any]:
    return {"filename": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}


def digest_table_files(paths: Iterable[Path]) -> str:
    """Hash the ordered table names and hashes without repackaging source data."""
    h = hashlib.sha256()
    for path in paths:
        h.update(path.name.encode("utf-8"))
        h.update(b"\0")
        h.update(sha256(path).encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


def parse_binned_qualifier(value: Any) -> tuple[float, float, float]:
    text = str(value).replace("−", "-")
    match = BIN_RE.search(text)
    if match is None:
        raise ValueError(f"qualifier lacks an explicit BIN range: {text!r}")
    center_text = text[: match.start()].strip()
    center_match = re.search(NUMBER, center_text)
    if center_match is None:
        raise ValueError(f"qualifier lacks a central value: {text!r}")
    center = float(center_match.group(0))
    low, high = map(float, match.groups())
    if not (math.isfinite(center) and math.isfinite(low) and math.isfinite(high)):
        raise ValueError(f"nonfinite qualifier: {text!r}")
    if not low < high:
        raise ValueError(f"invalid qualifier support: {text!r}")
    return center, low, high


def cubic_smoothstep(z: float) -> float:
    if z <= 0.0:
        return 0.0
    if z >= 1.0:
        return 1.0
    return 3.0 * z * z - 2.0 * z * z * z


def paper_factorization_fraction(
    ratio: float,
    *,
    r0: float = 0.10,
    width: float = 0.05,
    coefficient: float = 0.50,
    power: float = 2.0,
) -> float:
    """Equation (54) of arXiv:2608.27907 for a scalar qT/Q value."""
    if ratio < 0.0 or r0 <= 0.0 or width <= 0.0 or coefficient < 0.0:
        raise ValueError("invalid factorization-envelope input")
    return coefficient * cubic_smoothstep((ratio - r0) / width) * (ratio / r0) ** power


def support_domain(r_min: float, r_max: float) -> str:
    """Apply the existing candidate support policy without selecting rows."""
    if not 0.0 <= r_min <= r_max:
        raise ValueError("invalid qT/Q support")
    if r_max <= 0.15:
        return "pure_tmd_core"
    if r_min >= 0.30:
        return "pure_fixed_order_validation"
    return "matched_transition_or_mixed"


def quantiles(values: Iterable[float]) -> dict[str, float]:
    array = np.asarray(list(values), dtype=np.float64)
    probabilities = (0.0, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99, 1.0)
    names = ("min", "p10", "p25", "median", "p75", "p90", "p95", "p99", "max")
    return {name: float(value) for name, value in zip(names, np.quantile(array, probabilities))}


def _yaml_module():
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment-dependent message
        raise SystemExit(
            "PyYAML is required to read the official HEPData YAML archive; "
            "install PyYAML>=6 or use the project's source-analysis environment"
        ) from exc
    return yaml


def load_hepdata_rows(directory: Path) -> tuple[list[dict[str, Any]], list[Path]]:
    yaml = _yaml_module()
    paths = list(directory.glob("data*.yaml"))
    paths.sort(key=lambda path: int(TABLE_RE.search(path.name).group(1)))
    if len(paths) != 162:
        raise ValueError(f"expected 162 HEPData tables, found {len(paths)}")

    rows: list[dict[str, Any]] = []
    for path in paths:
        table_match = TABLE_RE.search(path.name)
        if table_match is None:
            raise ValueError(f"unexpected table filename: {path.name}")
        table = int(table_match.group(1))
        with path.open(encoding="utf-8") as stream:
            document = yaml.safe_load(stream)
        dependent = document["dependent_variables"]
        independent = document["independent_variables"]
        if len(dependent) != 3 or len(independent) != 1:
            raise ValueError(f"unexpected table structure: {path}")
        primary = dependent[0]
        transverse = independent[0]
        if len(primary["values"]) != len(transverse["values"]):
            raise ValueError(f"row-count mismatch: {path}")

        qualifiers = {str(item["name"]): item["value"] for item in primary["qualifiers"]}
        x, x_low, x_high = parse_binned_qualifier(qualifiers["$x$"])
        q2, q2_low, q2_high = parse_binned_qualifier(qualifiers["$Q^2$"])
        z, z_low, z_high = parse_binned_qualifier(qualifiers["$z$"])
        y = float(qualifiers["$y$"])
        header = str(primary["header"]["name"])
        charge = "h+" if "h^{+}" in header else "h-" if "h^{-}" in header else None
        if charge is None:
            raise ValueError(f"unrecognized primary observable: {header}")

        for row_number, (bin_value, measurement) in enumerate(
            zip(transverse["values"], primary["values"])
        ):
            pht2 = float(bin_value["value"])
            pht2_low = float(bin_value["low"])
            pht2_high = float(bin_value["high"])
            data = float(measurement["value"])
            errors = {str(item["label"]): float(item["symerror"]) for item in measurement["errors"]}
            if set(errors) != {"stat", "sys"}:
                raise ValueError(f"unexpected error fields in table {table}, row {row_number}")
            sigma_exp = math.hypot(errors["stat"], errors["sys"])
            r_center = math.sqrt(pht2) / (z * math.sqrt(q2))
            r_min = math.sqrt(pht2_low) / (z_high * math.sqrt(q2_high))
            r_max = math.sqrt(pht2_high) / (z_low * math.sqrt(q2_low))
            values = (x, x_low, x_high, q2, q2_low, q2_high, z, z_low, z_high,
                      y, pht2, pht2_low, pht2_high, data, sigma_exp, r_center, r_min, r_max)
            if not all(math.isfinite(value) for value in values) or data <= 0.0 or sigma_exp <= 0.0:
                raise ValueError(f"invalid numerical row in table {table}, row {row_number}")
            rows.append(
                {
                    "source_id": f"hepdata:ins1624692:v1:table{table}:row{row_number}",
                    "table": table,
                    "row": row_number,
                    "charge": charge,
                    "x": x,
                    "x_low": x_low,
                    "x_high": x_high,
                    "Q2_GeV2": q2,
                    "Q2_low_GeV2": q2_low,
                    "Q2_high_GeV2": q2_high,
                    "z": z,
                    "z_low": z_low,
                    "z_high": z_high,
                    "y": y,
                    "PhT2_GeV2": pht2,
                    "PhT2_low_GeV2": pht2_low,
                    "PhT2_high_GeV2": pht2_high,
                    "data": data,
                    "sigma_exp": sigma_exp,
                    "relative_sigma_exp": sigma_exp / abs(data),
                    "r_center": r_center,
                    "r_min": r_min,
                    "r_max": r_max,
                    "support_domain": support_domain(r_min, r_max),
                    "delta_center": paper_factorization_fraction(r_center),
                    "delta_support_max": paper_factorization_fraction(r_max),
                }
            )
    if len(rows) != 4664:
        raise ValueError(f"expected 4,664 primary rows, found {len(rows)}")
    if len({row["source_id"] for row in rows}) != len(rows):
        raise ValueError("duplicate official source row")
    return rows, paths


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def summarize_population(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("cannot summarize an empty population")
    result: dict[str, Any] = {
        "rows": len(rows),
        "tables": len({row["table"] for row in rows}),
        "charge_counts": dict(sorted(Counter(row["charge"] for row in rows).items())),
        "support_domain_counts": dict(sorted(Counter(row["support_domain"] for row in rows).items())),
        "r_center_quantiles": quantiles(row["r_center"] for row in rows),
        "r_support_min_quantiles": quantiles(row["r_min"] for row in rows),
        "r_support_max_quantiles": quantiles(row["r_max"] for row in rows),
        "relative_experimental_sigma_quantiles": quantiles(row["relative_sigma_exp"] for row in rows),
        "threshold_counts": {
            f"{threshold:.2f}": {
                "representative_value_at_or_below": sum(row["r_center"] <= threshold for row in rows),
                "full_support_at_or_below": sum(row["r_max"] <= threshold for row in rows),
            }
            for threshold in THRESHOLDS
        },
    }
    for location, field in (("representative_value", "delta_center"),
                            ("support_maximum", "delta_support_max")):
        deltas = np.asarray([row[field] for row in rows])
        sigma = np.asarray([row["sigma_exp"] for row in rows])
        data = np.abs(np.asarray([row["data"] for row in rows]))
        weights = sigma * sigma / (sigma * sigma + (data * deltas) ** 2)
        result[f"paper_envelope_at_{location}"] = {
            "delta_quantiles": quantiles(deltas),
            "rows_at_or_below_declared_delta_3_limit": int(np.count_nonzero(deltas <= 3.0)),
            "rows_above_declared_delta_3_limit": int(np.count_nonzero(deltas > 3.0)),
            "sum_independent_variance_weight": float(np.sum(weights)),
            "variance_weight_quantiles": quantiles(weights),
        }
    return result


def validate_selected_plan(
    selected_rows_path: Path,
    selected_official: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    plan_rows = [json.loads(line) for line in selected_rows_path.read_text().splitlines() if line]
    if len(plan_rows) != 1203:
        raise ValueError(f"expected 1,203 selected-plan rows, found {len(plan_rows)}")
    plan_ids = {row["official_observation_id"] for row in plan_rows}
    if plan_ids != set(selected_official):
        raise ValueError("selected adapter-plan and metric source IDs differ")
    max_bound_error = 0.0
    domain_mismatches = 0
    for row in plan_rows:
        official = selected_official[row["official_observation_id"]]
        bounds = row["nodewise_kinematics"]["full_rectangle_qT_over_Q_bounds"]
        max_bound_error = max(
            max_bound_error,
            abs(float(bounds["minimum"]) - official["r_min"]),
            abs(float(bounds["maximum"]) - official["r_max"]),
        )
        plan_domain = row["matching"]["support_domain"]
        expected = official["support_domain"]
        normalized = "matched_transition_or_mixed" if plan_domain == "matched_transition_or_mixed_support" else plan_domain
        domain_mismatches += normalized != expected
    if max_bound_error > 1e-12 or domain_mismatches:
        raise ValueError("official HEPData and selected adapter-plan support do not close")
    return {
        "rows": len(plan_rows),
        "source_id_set_equal": True,
        "maximum_absolute_qT_over_Q_bound_difference": max_bound_error,
        "support_domain_mismatches": domain_mismatches,
    }


def block_labels(manifest_rows: list[dict[str, Any]]) -> np.ndarray:
    labels = []
    for row in manifest_rows:
        if row["process"] == "DY":
            labels.append("DY")
        elif str(row["source_id"]).startswith("hepdata:ins1624692:"):
            labels.append("COMPASS")
        else:
            labels.append("HERMES")
    labels_array = np.asarray(labels)
    if Counter(labels_array) != {"DY": 743, "HERMES": 344, "COMPASS": 1203}:
        raise ValueError(f"unexpected metric blocks: {Counter(labels_array)}")
    return labels_array


def score_covariance(
    covariance: np.ndarray,
    residual: np.ndarray,
    labels: np.ndarray,
    high_compass_indices: np.ndarray,
    selected_compass_indices: np.ndarray,
    selected_compass_domains: np.ndarray,
    baseline_logdet: float,
) -> dict[str, Any]:
    factor = cho_factor(covariance, lower=True, check_finite=False)
    precision_residual = cho_solve(factor, residual, check_finite=False)
    contributions = residual * precision_residual
    q = float(np.sum(contributions))
    logdet = float(2.0 * np.sum(np.log(np.diag(factor[0]))))
    blocks = {
        label: {
            "rows": int(np.count_nonzero(labels == label)),
            "signed_quadratic_contribution": float(np.sum(contributions[labels == label])),
            "signed_contribution_per_row": float(np.mean(contributions[labels == label])),
        }
        for label in ("DY", "HERMES", "COMPASS")
    }
    high = contributions[high_compass_indices]
    blocks["high_COMPASS"] = {
        "rows": int(high.size),
        "signed_quadratic_contribution": float(np.sum(high)),
        "signed_contribution_per_row": float(np.mean(high)),
    }
    domains = {}
    for domain in ("pure_tmd_core", "matched_transition_or_mixed", "pure_fixed_order_validation"):
        local_mask = selected_compass_domains == domain
        domain_values = contributions[selected_compass_indices[local_mask]]
        domains[domain] = {
            "rows": int(domain_values.size),
            "signed_quadratic_contribution": float(np.sum(domain_values)),
            "signed_contribution_per_row": float(np.mean(domain_values)),
        }
    return {
        "q": q,
        "q_per_measurement": q / residual.size,
        "blocks": blocks,
        "COMPASS_support_domains": domains,
        "log_determinant": logdet,
        "log_determinant_change_from_experimental_covariance": logdet - baseline_logdet,
    }


def rescore_endpoint(
    metric_path: Path,
    metric_info_path: Path,
    endpoint_path: Path,
    manifest_rows: list[dict[str, Any]],
    official_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    with np.load(metric_path, allow_pickle=False) as archive:
        arrays = {name: archive[name].copy() for name in archive.files}
    with np.load(endpoint_path, allow_pickle=False) as archive:
        predictions = archive["values"].copy()
    data = arrays["data"]
    covariance = arrays["covariance"]
    if data.shape != (2290,) or predictions.shape != data.shape or covariance.shape != (2290, 2290):
        raise ValueError("unexpected metric or endpoint shape")
    labels = block_labels(manifest_rows)
    residual = data - predictions
    metric_info = load_json(metric_info_path)
    high = np.asarray(metric_info["high_COMPASS_indices"], dtype=np.int64)
    if high.size != 188 or np.any(labels[high] != "COMPASS"):
        raise ValueError("invalid high-COMPASS diagnostic indices")

    selected_indices = np.flatnonzero(labels == "COMPASS")
    selected_rows = [official_by_id[manifest_rows[index]["source_id"]] for index in selected_indices]
    selected_domains = np.asarray([row["support_domain"] for row in selected_rows])
    published_data = np.asarray([row["data"] for row in selected_rows])
    published_sigma = np.asarray([row["sigma_exp"] for row in selected_rows])
    if not np.array_equal(data[selected_indices], published_data):
        raise ValueError("metric data do not exactly match official COMPASS central values")
    sigma = np.sqrt(np.diag(covariance))
    if float(np.max(np.abs(sigma[selected_indices] - published_sigma))) > 2e-15:
        raise ValueError("metric COMPASS errors do not match quadrature stat/sys errors")
    compass_covariance = covariance[np.ix_(selected_indices, selected_indices)]
    compass_offdiag = compass_covariance - np.diag(np.diag(compass_covariance))
    noncompass_indices = np.flatnonzero(labels != "COMPASS")
    if np.max(np.abs(compass_offdiag)) != 0.0 or np.max(
        np.abs(covariance[np.ix_(selected_indices, noncompass_indices)])
    ) != 0.0:
        raise ValueError("diagnostic assumes the frozen COMPASS covariance block is diagonal and separate")

    baseline_factor = cho_factor(covariance, lower=True, check_finite=False)
    baseline_logdet = float(2.0 * np.sum(np.log(np.diag(baseline_factor[0]))))
    baseline = score_covariance(
        covariance,
        residual,
        labels,
        high,
        selected_indices,
        selected_domains,
        baseline_logdet,
    )
    variants: list[dict[str, Any]] = []
    for location, field in (("representative_value", "delta_center"),
                            ("support_maximum", "delta_support_max")):
        delta = np.asarray([row[field] for row in selected_rows])
        sigma_fact = np.abs(published_data) * delta
        for rho in (0.0, 0.5, 1.0):
            candidate = covariance.copy()
            candidate[selected_indices, selected_indices] += (1.0 - rho) * sigma_fact**2
            if rho:
                table_groups: dict[int, list[int]] = defaultdict(list)
                for local_index, row in enumerate(selected_rows):
                    table_groups[row["table"]].append(local_index)
                for local_group in table_groups.values():
                    local = np.asarray(local_group, dtype=np.int64)
                    global_group = selected_indices[local]
                    candidate[np.ix_(global_group, global_group)] += rho * np.outer(
                        sigma_fact[local], sigma_fact[local]
                    )
            score = score_covariance(
                candidate,
                residual,
                labels,
                high,
                selected_indices,
                selected_domains,
                baseline_logdet,
            )
            score.update(
                {
                    "factorization_ratio_location": location,
                    "within_table_correlation_fraction_rho": rho,
                    "covariance_definition": (
                        "C_exp + (1-rho) diag(sigma_fact^2) + "
                        "rho sum_table sigma_fact(table) sigma_fact(table)^T"
                    ),
                    "delta_at_or_below_3_rows": int(np.count_nonzero(delta <= 3.0)),
                    "delta_above_3_rows": int(np.count_nonzero(delta > 3.0)),
                    "sum_independent_variance_weight": float(
                        np.sum(published_sigma**2 / (published_sigma**2 + sigma_fact**2))
                    ),
                }
            )
            score["change_in_minus2logL_including_logdet"] = (
                score["q"] - baseline["q"]
                + score["log_determinant_change_from_experimental_covariance"]
            )
            variants.append(score)

    baseline["reproduces_saved_q_per_measurement"] = abs(
        baseline["q_per_measurement"] - 15.919207239379844
    ) <= 1e-12
    return {
        "scope": (
            "Saved-only score sensitivity on the existing 2,290-row endpoint; "
            "theory error is added to the 1,203 selected COMPASS rows only"
        ),
        "metric_compass_covariance": "diagonal stat^2+sys^2 with zero cross-process covariance",
        "baseline_experimental_covariance": baseline,
        "factorization_covariance_sensitivities": variants,
        "interpretation_guard": (
            "q/N values from different covariance definitions are not comparable fit-quality "
            "statistics by themselves; the log-determinant changes and the uncalibrated theory "
            "model must also be considered. Subset contributions are signed residual-times-"
            "precision-residual sums and can be negative when theory covariance correlates a "
            "subset with other rows"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hepdata-yaml", type=Path, required=True)
    parser.add_argument("--hepdata-archive", type=Path, required=True)
    parser.add_argument("--hepdata-record-json", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--selected-compass-rows", type=Path, required=True)
    parser.add_argument("--metric", type=Path, required=True)
    parser.add_argument("--metric-info", type=Path, required=True)
    parser.add_argument("--endpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows, table_paths = load_hepdata_rows(args.hepdata_yaml)
    official_by_id = {row["source_id"]: row for row in rows}
    manifest = load_json(args.source_manifest)
    manifest_rows = manifest["rows"]
    labels = block_labels(manifest_rows)
    selected_indices = np.flatnonzero(labels == "COMPASS")
    selected_ids = {manifest_rows[index]["source_id"] for index in selected_indices}
    if not selected_ids <= set(official_by_id):
        raise ValueError("metric contains COMPASS IDs absent from official HEPData")
    selected = [row for row in rows if row["source_id"] in selected_ids]
    not_selected = [row for row in rows if row["source_id"] not in selected_ids]
    coverage = {
        f"{threshold:.2f}": {
            "all_rows_with_full_support_at_or_below": sum(row["r_max"] <= threshold for row in rows),
            "selected_rows_with_full_support_at_or_below": sum(
                row["r_max"] <= threshold for row in selected
            ),
            "additional_rows_with_full_support_at_or_below": sum(
                row["r_max"] <= threshold for row in not_selected
            ),
        }
        for threshold in THRESHOLDS
    }
    plan_validation = validate_selected_plan(
        args.selected_compass_rows, {source_id: official_by_id[source_id] for source_id in selected_ids}
    )

    report = {
        "schema": "tmd-full-compass-reevaluation-v1",
        "status": "diagnostic_not_fit_authorized",
        "created_date": "2026-09-15",
        "scope": {
            "public_source": "HEPData ins1624692 version 1, DOI 10.17182/hepdata.83542.v1",
            "census": "all 4,664 primary multiplicity rows in 162 tables",
            "endpoint_rescoring": "existing 2,290-row width-8 update-658 saved endpoint",
            "new_row_predictions_computed": False,
            "frozen_likelihood_modified": False,
        },
        "inputs": {
            "hepdata_archive": file_receipt(args.hepdata_archive),
            "hepdata_record_json": file_receipt(args.hepdata_record_json),
            "hepdata_table_file_count": len(table_paths),
            "hepdata_ordered_table_digest": digest_table_files(table_paths),
            "source_manifest": file_receipt(args.source_manifest),
            "selected_compass_rows": file_receipt(args.selected_compass_rows),
            "metric": file_receipt(args.metric),
            "metric_info": file_receipt(args.metric_info),
            "endpoint": file_receipt(args.endpoint),
        },
        "support_policy": {
            "ratio": "qT/Q = sqrt(PhT2)/(z sqrt(Q2))",
            "bin_treatment": (
                "conservative Cartesian bounding-box extrema from published PhT2, z, and Q2 "
                "edges; not an event-level constrained-support reconstruction"
            ),
            "pure_tmd_core": "support maximum <= 0.15",
            "matched_transition_or_mixed": "not pure TMD and support minimum < 0.30",
            "pure_fixed_order_validation": "support minimum >= 0.30",
        },
        "paper_envelope_sensitivity": {
            "source": "arXiv:2608.27907 equations (52)-(56)",
            "formula": "sigma_fact=abs(data)*delta; delta=0.50*S((r-0.10)/0.05)*(r/0.10)^2",
            "smoothstep": "S=0 below 0, 3z^2-2z^3 on (0,1), 1 above 1",
            "paper_scope": "leading-power DY W-term stability study through representative qT/Q <= 0.20",
            "paper_declared_exclusion_trigger": "delta > 3; the paper's qT/Q <= 0.25 stage crossed it",
            "transfer_status": (
                "illustrative direct transfer only; not calibrated for bin-integrated SIDIS or "
                "for this matched W+Y/fixed-order prescription"
            ),
        },
        "full_COMPASS": summarize_population(rows),
        "currently_selected_COMPASS": summarize_population(selected),
        "additional_public_COMPASS": summarize_population(not_selected),
        "current_selection_coverage": coverage,
        "selected_adapter_plan_validation": plan_validation,
        "saved_endpoint_rescoring": rescore_endpoint(
            args.metric,
            args.metric_info,
            args.endpoint,
            manifest_rows,
            official_by_id,
        ),
        "decision_limits": [
            "The 3,461 additional public rows cannot enter a numerical fit until exact operators exist.",
            "Published one-dimensional bin edges do not determine the joint event-level support; the rectangular extrema used here are conservative bounds.",
            "The direct paper envelope is not a validated SIDIS theory covariance.",
            "Rows outside a TMD core need not be discarded, but their central theory must contain the applicable leading contribution; an uncertainty cannot replace a missing leading fixed-order/Y term.",
            "Correlation structure changes the endpoint conclusion materially and must be preregistered before fitting.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
