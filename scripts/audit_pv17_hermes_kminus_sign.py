#!/usr/bin/env python3
"""Diagnose the PV17 HERMES K- sign failures without fitting data.

The audit re-evaluates only the union of rows implicated by the stored fixed
matched contribution, the Gaussian control, or the transferred width-8
endpoint.  It exposes observable-level matching components, checks a refined
quadrature and a narrow-bin limit, and verifies the exact K-/target flavor map
encoded in the signed point operators.  Measurements stay in the ignored local
manifest and are never written to the public receipt.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np
import torch

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.audit_pv17_sidis_endpoint import (
    canonical_json,
    sha256_file,
    shard_receipt_identity_valid,
)
from scripts.run_pv17_sidis_point_pilot import (
    TARGET_MAP,
    build_inventory,
    load_foundation_read_only,
    narrow_bin_validation,
    observable_scale,
    point_density,
)
from tmdlab.models import Config, build, put
from tmdlab.pv17 import evaluate_sidis_point_arrays, validate_sidis_point_arrays


EXPECTED = {
    "implicated": 19,
    "fixed_nonpositive": 17,
    "Gaussian_nonpositive": 16,
    "endpoint_nonpositive": 16,
    "Gaussian_endpoint_overlap": 15,
    "signed_channels": 53760,
}


def observable_components(scalar: dict[str, Any]) -> dict[str, float]:
    kinematics = scalar["kinematics"]
    inclusive = scalar["inclusive_DIS"]
    pieces = scalar["pieces_per_dqT2"]
    scale = observable_scale(
        x=kinematics["x"],
        z=kinematics["z"],
        PhT=kinematics["PhT"],
        y=kinematics["y"],
        F2=inclusive["F2"],
        FL=inclusive["FL"],
    )
    transverse = 1 + (1 - kinematics["y"]) ** 2
    return {
        "W": float(scale * transverse * pieces["f_W"]),
        "FO_T": float(scale * transverse * pieces["FO_T"]),
        "FO_L": float(scale * 2 * (1 - kinematics["y"]) * pieces["FO_L"]),
        "minus_switched_ASY": float(-scale * transverse * pieces["f_ASY"]),
    }


def matching_role(weight: float) -> str:
    return "FO_only" if weight == 0 else "full_additive" if weight == 1 else "transition"


def sign(value: float) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def endpoint_products(model, arrays: dict[str, np.ndarray], lo: int, hi: int) -> np.ndarray:
    point_index = arrays["point_index"][lo:hi]
    selected = torch.as_tensor(
        arrays["coordinates"][point_index], dtype=torch.float64
    )
    species1 = torch.as_tensor(arrays["species1"][lo:hi], dtype=torch.int64)
    species2 = torch.as_tensor(arrays["species2"][lo:hi], dtype=torch.int64)
    with torch.no_grad():
        log_product = (
            model.incoming.log_multiplier(selected[:, 0], selected[:, 1], species1)
            + model.outgoing.log_multiplier(selected[:, 0], selected[:, 2], species2)
            + 2 * model.cs(selected[:, 0]) * torch.log(selected[:, 3] / model.Qref)
        )
        return torch.exp(log_product).cpu().numpy()


def flavor_contributions(
    model, arrays: dict[str, np.ndarray], row: int
) -> tuple[dict[str, float], dict[str, float]]:
    lo, hi = (int(value) for value in arrays["weight_offsets"][row:row + 2])
    if hi == lo:
        return {}, {}
    indices = arrays["point_index"][lo:hi]
    b = arrays["coordinates"][indices, 0]
    Gaussian_product = np.exp(-0.25 * b * b)
    trained_product = endpoint_products(model, arrays, lo, hi)
    result = []
    for products in (Gaussian_product, trained_product):
        grouped: defaultdict[int, float] = defaultdict(float)
        for pid, weight, product in zip(
            arrays["struck_pid"][lo:hi], arrays["weights"][lo:hi], products
        ):
            grouped[int(pid)] += float(weight * product)
        result.append({str(pid): value for pid, value in sorted(grouped.items())})
    return result[0], result[1]


def validate_flavor_map(arrays: dict[str, np.ndarray], row: int, target: str, *,
                        incoming: dict[int, int], outgoing: dict[tuple[str, int], int],
                        neutron) -> int:
    lo, hi = (int(value) for value in arrays["weight_offsets"][row:row + 2])
    checked = 0
    nucleons = set()
    for offset in range(lo, hi):
        pid = int(arrays["struck_pid"][offset])
        is_neutron = int(arrays["nucleon"][offset])
        nucleons.add(is_neutron)
        incoming_pid = neutron(pid) if is_neutron else pid
        if int(arrays["species1"][offset]) != incoming[incoming_pid]:
            raise ValueError("incoming proton-reference/isospin map mismatch")
        if int(arrays["species2"][offset]) != outgoing[("K+", -pid)]:
            raise ValueError("K- charge-conjugate outgoing map mismatch")
        checked += 1
    expected = {0} if target == "proton" else {0, 1}
    if nucleons != expected:
        raise ValueError("target component map mismatch")
    return checked


def load_kminus_operator_rows(campaign_dir: Path, model):
    rows: dict[int, dict[str, Any]] = {}
    shard_identities = []
    for receipt_path in sorted(campaign_dir.glob("shard-*.json")):
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        selected = [
            i for i, record in enumerate(receipt["records"])
            if record["experiment"] == "HERMES"
            and record["detected_hadron"] == "kminus"
        ]
        if not selected:
            continue
        if not shard_receipt_identity_valid(receipt):
            raise ValueError(f"shard receipt identity mismatch: {receipt_path}")
        arrays_path = receipt_path.with_suffix(".npz")
        if sha256_file(arrays_path) != receipt["arrays"]["npz_sha256"]:
            raise ValueError(f"shard array hash mismatch: {arrays_path}")
        with np.load(arrays_path, allow_pickle=False) as archive:
            arrays = {name: archive[name].copy() for name in archive.files}
        validate_sidis_point_arrays(arrays)
        predictions = evaluate_sidis_point_arrays(model, arrays).detach().cpu().numpy()
        shard_identities.append(receipt["identity"])
        for local_row in selected:
            record = receipt["records"][local_row]
            index = int(record["selected_index"])
            if index in rows:
                raise ValueError("duplicate selected index in K- shards")
            rows[index] = {
                "record": record,
                "arrays": arrays,
                "local_row": local_row,
                "fixed": float(arrays["fixed_predictions"][local_row]),
                "Gaussian": float(arrays["Gaussian_controls"][local_row]),
                "endpoint": float(predictions[local_row]),
            }
    if len(rows) != 376:
        raise ValueError("complete 376-row HERMES K- population required")
    return rows, shard_identities


def audit(args) -> dict[str, Any]:
    campaign = json.loads(args.campaign_receipt.read_text(encoding="utf-8"))
    endpoint_receipt = json.loads(args.endpoint_receipt.read_text(encoding="utf-8"))
    result = json.loads(args.result.read_text(encoding="utf-8"))
    if sha256_file(args.endpoint) != result["audit"]["endpoint_sha256"]:
        raise ValueError("endpoint/result hash mismatch")
    if endpoint_receipt["transferred_endpoint"]["result_identity"] != result["identity"]:
        raise ValueError("endpoint feasibility/result identity mismatch")
    if endpoint_receipt["campaign"]["identity"] != campaign["identity"]:
        raise ValueError("endpoint feasibility/campaign identity mismatch")

    with np.load(args.endpoint, allow_pickle=False) as archive:
        theta = archive["theta"].copy()
    model = build(Config(width=8, depth=1))
    put(model, theta)
    model.eval()
    operator_rows, shard_identities = load_kminus_operator_rows(args.campaign_dir, model)

    fixed_bad = {index for index, item in operator_rows.items() if item["fixed"] <= 0}
    Gaussian_bad = {index for index, item in operator_rows.items() if item["Gaussian"] <= 0}
    endpoint_bad = {index for index, item in operator_rows.items() if item["endpoint"] <= 0}
    implicated = fixed_bad | Gaussian_bad | endpoint_bad
    if endpoint_bad != set(endpoint_receipt["nonpositive"]["endpoint_selected_indices"]):
        raise ValueError("endpoint nonpositive set changed")
    if Gaussian_bad != set(
        endpoint_receipt["nonpositive"]["Gaussian_control_selected_indices"]
    ):
        raise ValueError("Gaussian nonpositive set changed")

    manifest_payload = args.manifest.read_bytes()
    manifest_rows = [json.loads(line) for line in manifest_payload.splitlines() if line.strip()]
    selected = {
        int(row["selected_index"]): row
        for row in manifest_rows
        if row.get("selected_index") in implicated
    }
    if set(selected) != implicated or any(
        row["experiment"] != "HERMES" or row["detected_hadron"] != "kminus"
        for row in selected.values()
    ):
        raise ValueError("implicated manifest population mismatch")

    pre_inventory = build_inventory(args.foundation_root)
    runtime = load_foundation_read_only(
        args.foundation_root, args.prebuilt_library, args.prebuilt_provenance_receipt
    )
    import lhapdf
    from work.direct_fit_launch_inputs.delivered import neutron
    from work.direct_fit_launch_sidis.flavors import INCOMING, OUTGOING, identity
    from work.regional_matching.service import RegionalConfig, RegionalService

    lhapdf.setVerbosity(0)
    services = {}
    records = []
    checked_channels = 0
    try:
        for target in sorted({row["target"] for row in selected.values()}):
            services[target] = RegionalService(
                RegionalConfig(
                    target=TARGET_MAP[target], hadron="K-", pdf_xmin=0.003, ff_zmin=0.2
                )
            )
        for index in sorted(implicated):
            row = selected[index]
            operator = operator_rows[index]
            service = services[row["target"]]
            scalar = point_density(service, row, b_order=12, fraction=4, b_stop=16.0)
            refined = point_density(service, row, b_order=24, fraction=8, b_stop=24.0)
            narrow = narrow_bin_validation(
                service, row, scalar, relative_width=1e-3, b_order=24, fraction=8
            )
            components = observable_components(scalar)
            refined_components = observable_components(refined)
            fixed_from_components = (
                components["FO_T"]
                + components["FO_L"]
                + components["minus_switched_ASY"]
            )
            total_from_components = fixed_from_components + components["W"]
            Gaussian_flavors, endpoint_flavors = flavor_contributions(
                model, operator["arrays"], operator["local_row"]
            )
            checked_channels += validate_flavor_map(
                operator["arrays"],
                operator["local_row"],
                row["target"],
                incoming=INCOMING,
                outgoing=OUTGOING,
                neutron=neutron,
            )
            records.append(
                {
                    "selected_index": index,
                    "target": row["target"],
                    "matching_role": matching_role(scalar["transition_weight"]),
                    "qT_over_Q": float(scalar["kinematics"]["qT_over_Q"]),
                    "active_nf_hard_and_recoil": int(scalar["nf_hard_and_recoil"]),
                    "active_nf_OPE": scalar["nf_OPE_sampled"],
                    "observable_components": components,
                    "fixed_from_components": fixed_from_components,
                    "Gaussian_total_from_components": total_from_components,
                    "stored_fixed": operator["fixed"],
                    "stored_Gaussian": operator["Gaussian"],
                    "transferred_endpoint": operator["endpoint"],
                    "transferred_endpoint_W": operator["endpoint"] - operator["fixed"],
                    "Gaussian_W_by_struck_pid": Gaussian_flavors,
                    "transferred_endpoint_W_by_struck_pid": endpoint_flavors,
                    "refined_total": float(refined["multiplicity_per_dPhT"]),
                    "refined_components": refined_components,
                    "refined_minus_baseline": float(
                        refined["multiplicity_per_dPhT"] - scalar["multiplicity_per_dPhT"]
                    ),
                    "narrow_bin_total": float(narrow["multiplicity_per_dPhT"]),
                    "narrow_bin_relative_difference": float(
                        narrow["multiplicity_relative_difference"]
                    ),
                    "narrow_bin_component_max_relative_difference": float(
                        narrow["component_max_relative_difference"]
                    ),
                    "baseline_W_rule_refinement_abs_per_dqT2": float(
                        scalar["numerical_indicators"]["W_b_rule_refinement_abs"]
                    ),
                    "sign_flags": {
                        "fixed_nonpositive": operator["fixed"] <= 0,
                        "Gaussian_nonpositive": operator["Gaussian"] <= 0,
                        "endpoint_nonpositive": operator["endpoint"] <= 0,
                    },
                }
            )
    finally:
        for service in services.values():
            service.close()
    build_unchanged = build_inventory(args.foundation_root) == pre_inventory

    maxima = {
        "direct_component_to_stored_fixed_abs": max(
            abs(record["fixed_from_components"] - record["stored_fixed"])
            for record in records
        ),
        "direct_component_to_stored_Gaussian_abs": max(
            abs(record["Gaussian_total_from_components"] - record["stored_Gaussian"])
            for record in records
        ),
        "refined_total_change_abs": max(
            abs(record["refined_minus_baseline"]) for record in records
        ),
        "narrow_bin_relative_difference": max(
            record["narrow_bin_relative_difference"] for record in records
        ),
        "narrow_bin_component_relative_difference": max(
            record["narrow_bin_component_max_relative_difference"] for record in records
        ),
        "baseline_W_rule_refinement_abs_per_dqT2": max(
            record["baseline_W_rule_refinement_abs_per_dqT2"] for record in records
        ),
    }
    fixed_cancellation = sum(
        record["observable_components"]["FO_T"]
        + record["observable_components"]["FO_L"]
        < -record["observable_components"]["minus_switched_ASY"]
        for record in records
    )
    signs_stable = all(
        sign(record["stored_Gaussian"]) == sign(record["refined_total"])
        == sign(record["narrow_bin_total"])
        for record in records
    )
    invariants = {
        "exact_19_implicated_rows": len(implicated) == EXPECTED["implicated"],
        "exact_17_fixed_nonpositive": len(fixed_bad) == EXPECTED["fixed_nonpositive"],
        "exact_16_Gaussian_nonpositive": len(Gaussian_bad)
        == EXPECTED["Gaussian_nonpositive"],
        "exact_16_endpoint_nonpositive": len(endpoint_bad)
        == EXPECTED["endpoint_nonpositive"],
        "exact_15_Gaussian_endpoint_overlap": len(Gaussian_bad & endpoint_bad)
        == EXPECTED["Gaussian_endpoint_overlap"],
        "all_implicated_rows_transition_or_full_additive": all(
            record["matching_role"] in {"transition", "full_additive"}
            for record in records
        ),
        "all_implicated_rows_nf4": all(
            record["active_nf_hard_and_recoil"] == 4
            and record["active_nf_OPE"] == [4]
            for record in records
        ),
        "all_signed_channels_follow_Kminus_charge_conjugation_and_target_map": (
            checked_channels == EXPECTED["signed_channels"]
        ),
        "direct_components_recover_stored_controls": (
            maxima["direct_component_to_stored_fixed_abs"] < 2e-12
            and maxima["direct_component_to_stored_Gaussian_abs"] < 2e-12
        ),
        "all_signs_stable_under_refinement_and_narrow_bin_limit": signs_stable,
        "exact_17_ASY_over_FO_cancellations": fixed_cancellation == 17,
        "foundation_build_inventory_unchanged": build_unchanged,
    }
    if not all(invariants.values()):
        raise ValueError(
            f"HERMES K- sign diagnostic invariant failed: "
            f"{[name for name, passed in invariants.items() if not passed]}"
        )

    foundation_files = (
        "work/direct_fit_launch_sidis/flavors.py",
        "work/hermes_kaon_channel_extension/API.md",
        "work/hermes_kaon_channel_extension/ANALYSIS.json",
        "work/hermes_kaon_channel_extension/QA_RECEIPT.json",
        "work/regional_matching/service.py",
        "work/regional_matching/panel.py",
        "work/regional_matching/w.py",
    )
    receipt = {
        "schema": "pv17-hermes-kminus-sign-diagnostic-v1",
        "status": "central_theory_matching_sign_failure_numerically_reproduced",
        "counts": {
            "HERMES_Kminus_population": len(operator_rows),
            "implicated_union": len(implicated),
            "fixed_nonpositive": len(fixed_bad),
            "Gaussian_nonpositive": len(Gaussian_bad),
            "endpoint_nonpositive": len(endpoint_bad),
            "Gaussian_endpoint_overlap": len(Gaussian_bad & endpoint_bad),
            "ASY_exceeds_FO_T_plus_FO_L": fixed_cancellation,
            "signed_channels_checked": checked_channels,
            "by_target": dict(sorted(Counter(record["target"] for record in records).items())),
            "by_matching_role": dict(
                sorted(Counter(record["matching_role"] for record in records).items())
            ),
        },
        "sets": {
            "implicated_selected_indices": sorted(implicated),
            "fixed_nonpositive_selected_indices": sorted(fixed_bad),
            "Gaussian_nonpositive_selected_indices": sorted(Gaussian_bad),
            "endpoint_nonpositive_selected_indices": sorted(endpoint_bad),
        },
        "numerical_maxima": maxima,
        "records": records,
        "flavor_map": {
            "identity": identity(),
            "Kminus_rule": "outgoing K+ reference with charge-conjugated struck PID",
            "deuteron_rule": "equal proton/neutron components; u<->d on incoming proton reference",
            "interpretation": "exact implementation map passes; this does not validate the physical FF choice",
        },
        "interpretation": {
            "classification": "not_operator_serialization_or_coarse_quadrature",
            "finding": (
                "The switched ASY term exceeds FO_T+FO_L in 17 rows. The signed "
                "Fourier-Bessel W term changes which marginal rows are rescued, but the "
                "transferred endpoint leaves 16 nonpositive predictions."
            ),
            "legacy_kaon_pilot_scope": (
                "The earlier integrated fixed-nf4 kaon pilot verifies charge conjugation and "
                "target maps but explicitly has full_numerical_qualification=false and is not "
                "closure for these average-point regional predictions."
            ),
            "production_authorized": False,
        },
        "invariants": invariants,
        "source_receipts": {
            "manifest_sha256": hashlib.sha256(manifest_payload).hexdigest(),
            "campaign_identity": campaign["identity"],
            "Kminus_shard_identities": shard_identities,
            "endpoint_feasibility_identity": endpoint_receipt["identity"],
            "endpoint_result_identity": result["identity"],
            "endpoint_sha256": sha256_file(args.endpoint),
            "prebuilt_binary_sha256": runtime["binary_sha256"],
            "prebuilt_provenance_receipt_sha256": runtime[
                "provenance_receipt_sha256"
            ],
            "producer_sources": {
                "scripts/audit_pv17_hermes_kminus_sign.py": sha256_file(Path(__file__)),
                "scripts/run_pv17_sidis_point_pilot.py": sha256_file(
                    Path(__file__).resolve().parent / "run_pv17_sidis_point_pilot.py"
                ),
                "tmdlab/models.py": sha256_file(
                    Path(__file__).resolve().parents[1] / "tmdlab/models.py"
                ),
                "tmdlab/pv17.py": sha256_file(
                    Path(__file__).resolve().parents[1] / "tmdlab/pv17.py"
                ),
            },
            "foundation_sources": {
                name: sha256_file(args.foundation_root / name) for name in foundation_files
            },
            "foundation_build_inventory_sha256": hashlib.sha256(
                canonical_json(pre_inventory).encode("utf-8")
            ).hexdigest(),
        },
        "scope": {
            "CPU_only": True,
            "optimizer_run": False,
            "measurements_written": False,
            "physics_changed": False,
        },
        "next_gate": (
            "Review whether the point-observable additive matching and current kaon "
            "collinear input are scientifically valid in this high-x low-PhT corner. "
            "Do not fit or hide the failure with covariance inflation."
        ),
    }
    receipt["identity"] = hashlib.sha256(
        canonical_json(receipt).encode("utf-8")
    ).hexdigest()
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--foundation-root", type=Path, required=True)
    parser.add_argument("--prebuilt-library", type=Path, required=True)
    parser.add_argument("--prebuilt-provenance-receipt", type=Path, required=True)
    parser.add_argument("--campaign-dir", type=Path, required=True)
    parser.add_argument("--campaign-receipt", type=Path, required=True)
    parser.add_argument("--endpoint", type=Path, required=True)
    parser.add_argument("--endpoint-receipt", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("refuse to overwrite public HERMES K- sign receipt")
    receipt = audit(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(canonical_json({"identity": receipt["identity"], "status": receipt["status"]}))


if __name__ == "__main__":
    main()
