#!/usr/bin/env python3
"""Build a bounded current-theory point-operator pilot for PV17 SIDIS.

The immutable foundation tree is imported read-only.  A previously compiled,
hash-verified regional native library is loaded directly so this script never
invokes the foundation compiler or writes into that tree.
"""

from __future__ import annotations

import argparse
import ctypes as ct
import hashlib
import json
import math
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.special import j0

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.audit_pv17_sidis_domain import BEAM_CONVENTIONS, canonical_json
from tmdlab.models import Config as DNNConfig
from tmdlab.models import build as build_dnn
from tmdlab.models import flat as flatten_dnn
from tmdlab.models import put as put_dnn
from tmdlab.pv17 import evaluate_sidis_point_arrays, validate_sidis_point_arrays


HERMES_PILOT_SELECTED_INDEX = 389
COMPASS_PILOT_GROUP = "COMPASS_piminus_spectrum_007"
HADRON_MAP = {"piplus": "pi+", "piminus": "pi-", "kplus": "K+", "kminus": "K-"}
TARGET_MAP = {"proton": "proton", "deuteron": "isoscalar"}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def array_receipt(value: np.ndarray) -> dict[str, Any]:
    contiguous = np.ascontiguousarray(value)
    return {
        "shape": list(contiguous.shape),
        "dtype": str(contiguous.dtype),
        "bytes_sha256": sha256_bytes(contiguous.tobytes(order="C")),
    }


def transition_weight(ratio: float) -> float:
    """Current 0.15--0.30 one-minus-quintic transition."""
    if not math.isfinite(ratio) or ratio < 0:
        raise ValueError("finite nonnegative qT/Q required")
    if ratio <= 0.15:
        return 1.0
    if ratio >= 0.30:
        return 0.0
    t = (ratio - 0.15) / 0.15
    return 1 - (6 * t**5 - 15 * t**4 + 10 * t**3)


def observable_scale(*, x: float, z: float, PhT: float, y: float, F2: float, FL: float) -> float:
    """Scale dqT2 hadronic functions to the legacy dM/dPhT observable."""
    Y = 1 + (1 - y) ** 2
    denominator = Y * F2 - y * y * FL
    if not all(math.isfinite(v) for v in (x, z, PhT, y, F2, FL, denominator)):
        raise ValueError("finite point-observable inputs required")
    if not 0 < x < 1 or not 0 < z < 1 or PhT <= 0 or denominator <= 0:
        raise ValueError("physical point-observable inputs required")
    return 2 * PhT * x / (z * z * denominator)


def multiplicity_from_pieces(
    *,
    x: float,
    z: float,
    PhT: float,
    y: float,
    F2: float,
    FL: float,
    f_W: float,
    FO_T: float,
    FO_L: float,
    f_ASY: float,
) -> float:
    scale = observable_scale(x=x, z=z, PhT=PhT, y=y, F2=F2, FL=FL)
    Y = 1 + (1 - y) ** 2
    return scale * (Y * (f_W + FO_T - f_ASY) + 2 * (1 - y) * FO_L)


def select_pilot_rows(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    selected = [row for row in rows if row.get("selected_by_kinematic_cuts")]
    hermes = [row for row in selected if row.get("selected_index") == HERMES_PILOT_SELECTED_INDEX]
    if len(hermes) != 1 or hermes[0]["experiment"] != "HERMES":
        raise ValueError("unique registered HERMES pilot row not found")
    compass = [
        row
        for row in selected
        if row.get("normalization", {}).get("group") == COMPASS_PILOT_GROUP
    ]
    compass.sort(key=lambda row: row["selected_index"])
    if len(compass) != 22 or sum(not row["contributes_to_published_point_count"] for row in compass) != 1:
        raise ValueError("registered COMPASS pilot spectrum is incomplete")
    denominator_id = compass[0]["normalization"]["denominator_source_id"]
    if not compass[0]["normalization"]["is_fixed_denominator"] or any(
        row["normalization"]["denominator_source_id"] != denominator_id for row in compass
    ):
        raise ValueError("COMPASS pilot denominator contract changed")
    return hermes[0], compass


def _configure_prebuilt_library(binary: Path, provenance: dict[str, Any]):
    if sha256_file(binary) != provenance["binary_sha256"]:
        raise ValueError("prebuilt regional library hash mismatch")
    for path, expected in provenance["build_inputs"].items():
        if sha256_file(Path(path)) != expected:
            raise ValueError(f"prebuilt regional library input changed: {path}")
    lib = ct.CDLL(str(binary))
    lib.delivered_error.restype = ct.c_char_p
    lib.delivered_create.argtypes = [ct.c_int] * 6 + [ct.c_double] * 5 + [ct.c_char_p] * 3
    lib.delivered_create.restype = ct.c_void_p
    lib.delivered_close.argtypes = [ct.c_void_p]
    lib.delivered_close.restype = ct.c_int
    lib.delivered_value.argtypes = [ct.c_void_p] + [ct.c_int] * 3 + [ct.c_double] * 2 + [ct.c_int]
    lib.delivered_value.restype = ct.c_double
    lib.delivered_dis.argtypes = [ct.c_void_p] + [ct.c_double] * 2 + [ct.c_int]
    lib.delivered_dis.restype = ct.c_double
    lib.delivered_alpha.argtypes = [ct.c_void_p, ct.c_double]
    lib.delivered_alpha.restype = ct.c_double
    pointer = np.ctypeslib.ndpointer(dtype=np.float64, ndim=1, flags="C_CONTIGUOUS")
    lib.bttmd_recoil_closed_accumulate.argtypes = (
        [ct.c_void_p] * 2 + [ct.c_double] * 4 + [ct.c_int] * 3 + [pointer] * 4
    )
    lib.bttmd_recoil_closed_accumulate.restype = ct.c_int
    return lib


def load_foundation_read_only(
    foundation_root: Path, binary: Path, provenance_receipt: Path
) -> dict[str, Any]:
    root = foundation_root.resolve()
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(root), str(root / "src")]
    from work.regional_matching import panel

    receipt = json.loads(provenance_receipt.read_text(encoding="utf-8"))
    provenance = receipt["provenance"][0]
    lib = _configure_prebuilt_library(binary.resolve(), provenance)
    if panel._libraries:
        raise ValueError("regional panel library cache was populated before read-only injection")
    panel._libraries["pv17-read-only-prebuilt"] = (lib, provenance)
    return {
        "root": root,
        "binary_sha256": provenance["binary_sha256"],
        "provenance_receipt_sha256": sha256_file(provenance_receipt),
        "build_inputs": provenance["build_inputs"],
    }


def build_inventory(root: Path) -> tuple[tuple[str, str], ...]:
    directory = root / "work/regional_matching/_build"
    return tuple(
        (str(path.relative_to(root)), sha256_file(path))
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    )


def row_kinematics(row: dict[str, Any]) -> dict[str, float]:
    raw = row["raw"]
    x, z = float(raw["x"]), float(raw["z"])
    Q2, PhT = float(raw["Q2_GeV2"]), float(raw["PhT_GeV"])
    beam = BEAM_CONVENTIONS[row["experiment"]]
    Q = math.sqrt(Q2)
    qT = PhT / z
    return {
        "x": x,
        "z": z,
        "Q": Q,
        "Q2": Q2,
        "PhT": PhT,
        "qT": qT,
        "qT2": qT * qT,
        "qT_over_Q": qT / Q,
        "y": Q2 / (x * beam["S_lN_GeV2"]),
    }


def _b_rule(model, service, qT: float, order: int, b_stop: float, nodes):
    edges = sorted(
        {
            0.0,
            b_stop,
            *(value for value in (0.025, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4) if value < b_stop),
            *model.profile.crossings(service.edges[1:-1], b_stop),
        }
    )
    return [
        (float(b), float(weight), float(j0(qT * b)))
        for low, high in zip(edges, edges[1:])
        for b, weight in nodes(low, high, order)
    ]


def point_density(service, row: dict[str, Any], *, b_order: int = 12, fraction: int = 4,
                  b_stop: float = 16.0) -> dict[str, Any]:
    from bttmd_foundation.sidis_common_w import subtraction_polynomial
    from bttmd_foundation.sidis_uv_subtraction import UVLogProjection
    from work.conditional_delivered_sidis_pilot.pilot import denominator, nodes
    from work.regional_matching.panel import recoil
    from work.regional_matching.w import RegionalW

    k = row_kinematics(row)
    x, z, Q, qT2 = k["x"], k["z"], k["Q"], k["qT2"]
    f = transition_weight(k["qT_over_Q"])
    panel = service.at(Q)
    a_s = service.a_s(Q)
    fixed_order, fixed_order_error = recoil(panel, x, z, Q, qT2, fraction)
    FO_T, FO_L = (a_s * float(value) for value in fixed_order)
    FO_error = (a_s * fixed_order_error).tolist()
    if f:
        polynomial = subtraction_polynomial(panel, x, z, Q).strict_w.coefficients[1]
        subtraction = UVLogProjection(Q).subtraction_density(
            polynomial, qT_GeV=k["qT"], epsabs=2e-8, epsrel=2e-6
        )
        f_ASY = f * a_s * subtraction.value
        model = RegionalW(service, x=x, z=z, Q=Q, g=0.25)
        values = []
        active = set()
        for order in (b_order, 2 * b_order):
            total = 0.0
            for b, weight, radial in _b_rule(model, service, k["qT"], order, b_stop, nodes):
                point = model.point(b)
                active.add(service.coupling.n_f_at(point.mu_b_GeV))
                total += weight * b / 2 * radial * point.value
            values.append(total)
        f_W = f * values[-1]
        W_refinement = abs(f * (values[-1] - values[0]))
        ASY_error = f * a_s * subtraction.numerical_absolute_estimate
    else:
        f_W = f_ASY = W_refinement = ASY_error = 0.0
        active = set()

    inclusive = denominator(panel, x, Q)
    pieces = {"f_W": f_W, "FO_T": FO_T, "FO_L": FO_L, "f_ASY": f_ASY}
    prediction = multiplicity_from_pieces(
        x=x,
        z=z,
        PhT=k["PhT"],
        y=k["y"],
        F2=inclusive["F2"],
        FL=inclusive["FL"],
        **pieces,
    )
    return {
        "kinematics": k,
        "transition_weight": f,
        "pieces_per_dqT2": pieces,
        "inclusive_DIS": {"F2": inclusive["F2"], "FL": inclusive["FL"]},
        "multiplicity_per_dPhT": prediction,
        "numerical_indicators": {
            "W_b_rule_refinement_abs": W_refinement,
            "FO_fraction_abs_T_L": FO_error,
            "ASY_abs": ASY_error,
            "b_order": b_order,
            "b_stop_GeV_inv": b_stop,
        },
        "nf_hard_and_recoil": panel.n_f,
        "nf_OPE_sampled": sorted(active),
    }


def build_point_operator(proton_service, target_service, row: dict[str, Any], scalar: dict[str, Any],
                         *, b_order: int = 24, b_stop: float = 16.0) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    from work.conditional_delivered_sidis_pilot.pilot import nodes
    from work.direct_fit_launch_sidis.flavors import canonical_channels
    from work.regional_matching.w import RegionalW

    k = scalar["kinematics"]
    x, z, Q, qT = k["x"], k["z"], k["Q"], k["qT"]
    f = scalar["transition_weight"]
    inclusive = scalar["inclusive_DIS"]
    scale = observable_scale(
        x=x, z=z, PhT=k["PhT"], y=k["y"], F2=inclusive["F2"], FL=inclusive["FL"]
    )
    Y = 1 + (1 - k["y"]) ** 2
    fixed = scale * (
        Y * (scalar["pieces_per_dqT2"]["FO_T"] - scalar["pieces_per_dqT2"]["f_ASY"])
        + 2 * (1 - k["y"]) * scalar["pieces_per_dqT2"]["FO_L"]
    )

    coordinates = []
    weights = []
    point_index = []
    species1 = []
    species2 = []
    active_nf = []
    nucleon = []
    struck_pid = []
    if f:
        model = RegionalW(proton_service, x=x, z=z, Q=Q, g=0.0)
        for b, weight, radial in _b_rule(model, proton_service, qT, b_order, b_stop, nodes):
            profile = model.profile.point(b)
            mu = profile.mu_i_GeV
            nf = proton_service.coupling.n_f_at(mu)
            pdf, ff = proton_service.canonical_legs(x, z, mu)
            channels = canonical_channels(
                {pid: value.coefficients for pid, value in pdf.items()},
                {pid: value.coefficients for pid, value in ff.items()},
                target=TARGET_MAP[row["target"]],
                hadron=HADRON_MAP[row["detected_hadron"]],
                nf=nf,
                a_s=proton_service.a_s(mu),
            )
            evolution = model.evolution.symmetric_pair_factor(
                b_GeV_inv=profile.b_pert_GeV_inv,
                mu_i_GeV=mu,
                zeta_i_GeV2=profile.zeta_i_GeV2,
                mu_f_GeV=Q,
                zeta_f_GeV2=Q * Q,
            )
            common = scale * Y * f * weight * b / 2 * radial * model.hard * evolution
            index = len(coordinates)
            coordinates.append((b, x, z, Q))
            active_nf.append(nf)
            for channel in channels:
                weights.append(common * channel.weight)
                point_index.append(index)
                species1.append(channel.incoming_species)
                species2.append(channel.outgoing_species)
                nucleon.append(int(channel.nucleon == "neutron"))
                struck_pid.append(channel.struck_pid)

    arrays = {
        "coordinates": np.asarray(coordinates, dtype=np.float64).reshape((-1, 4)),
        "weights": np.asarray(weights, dtype=np.float64),
        "point_index": np.asarray(point_index, dtype=np.int64),
        "species1": np.asarray(species1, dtype=np.int64),
        "species2": np.asarray(species2, dtype=np.int64),
        "active_nf": np.asarray(active_nf, dtype=np.int8),
        "nucleon": np.asarray(nucleon, dtype=np.int8),
        "struck_pid": np.asarray(struck_pid, dtype=np.int8),
    }
    W_gaussian = float(
        np.sum(
            arrays["weights"]
            * np.exp(-0.25 * arrays["coordinates"][arrays["point_index"], 0] ** 2)
        )
    ) if len(arrays["weights"]) else 0.0
    gaussian = fixed + W_gaussian
    metadata = {
        "fixed_prediction": fixed,
        "Gaussian_W_prediction": W_gaussian,
        "Gaussian_control": gaussian,
        "Gaussian_scalar_prediction": scalar["multiplicity_per_dPhT"],
        "Gaussian_absolute_recovery_error": abs(gaussian - scalar["multiplicity_per_dPhT"]),
        "coordinates": len(arrays["coordinates"]),
        "signed_weights": len(arrays["weights"]),
        "negative_weights": int(np.count_nonzero(arrays["weights"] < 0)),
        "b_order": b_order,
        "b_stop_GeV_inv": b_stop,
        "NP_in_weights": False,
    }
    return arrays, metadata


def narrow_bin_validation(service, row: dict[str, Any], scalar: dict[str, Any], *, relative_width: float,
                          b_order: int = 12, fraction: int = 4) -> dict[str, Any]:
    from work.regional_matching.pilot import point

    k = scalar["kinematics"]
    half = k["qT2"] * relative_width / 2
    low, high = k["qT2"] - half, k["qT2"] + half
    integrated = point(
        service,
        k["x"],
        k["z"],
        k["Q"],
        low,
        high,
        transverse=4,
        fraction=fraction,
        b_order=b_order,
        b_stop=16.0,
        g=0.25,
    )
    width = high - low
    densities = {name: value / width for name, value in integrated["pieces"].items()}
    prediction = multiplicity_from_pieces(
        x=k["x"],
        z=k["z"],
        PhT=k["PhT"],
        y=k["y"],
        F2=scalar["inclusive_DIS"]["F2"],
        FL=scalar["inclusive_DIS"]["FL"],
        **densities,
    )
    central = scalar["multiplicity_per_dPhT"]
    component_relative = {
        name: abs(densities[name] - scalar["pieces_per_dqT2"][name])
        / max(1e-300, abs(scalar["pieces_per_dqT2"][name]), abs(densities[name]))
        for name in densities
        if scalar["pieces_per_dqT2"][name] != 0 or densities[name] != 0
    }
    return {
        "relative_qT2_width": relative_width,
        "multiplicity_per_dPhT": prediction,
        "multiplicity_relative_difference": abs(prediction - central) / max(abs(central), 1e-300),
        "component_max_relative_difference": max(component_relative.values(), default=0.0),
        "component_relative_differences": component_relative,
    }


def concatenate_operators(items: list[tuple[dict[str, np.ndarray], dict[str, Any]]]) -> dict[str, np.ndarray]:
    coordinate_offsets = [0]
    weight_offsets = [0]
    arrays = {name: [] for name in ("coordinates", "weights", "point_index", "species1", "species2", "active_nf", "nucleon", "struck_pid")}
    fixed = []
    gaussian = []
    for operator, metadata in items:
        coordinate_offset = coordinate_offsets[-1]
        for name, value in operator.items():
            if name == "point_index":
                value = value + coordinate_offset
            arrays[name].append(value)
        coordinate_offsets.append(coordinate_offset + len(operator["coordinates"]))
        weight_offsets.append(weight_offsets[-1] + len(operator["weights"]))
        fixed.append(metadata["fixed_prediction"])
        gaussian.append(metadata["Gaussian_control"])
    result = {}
    for name, values in arrays.items():
        if name == "coordinates":
            result[name] = np.concatenate(values, axis=0) if values else np.empty((0, 4), dtype=np.float64)
        else:
            result[name] = np.concatenate(values) if values else np.asarray([])
    result.update(
        coordinate_offsets=np.asarray(coordinate_offsets, dtype=np.int64),
        weight_offsets=np.asarray(weight_offsets, dtype=np.int64),
        fixed_predictions=np.asarray(fixed, dtype=np.float64),
        Gaussian_controls=np.asarray(gaussian, dtype=np.float64),
    )
    return result


def replay_current_dnn(arrays: dict[str, np.ndarray]) -> dict[str, Any]:
    """Replay the registered Gaussian start and a denominator-only ratio gradient."""
    import torch

    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    rows = validate_sidis_point_arrays(arrays)
    if rows != 23 or arrays["weight_offsets"][4] != arrays["weight_offsets"][3]:
        raise ValueError("registered fixed-only COMPASS numerator changed")
    model = build_dnn(DNNConfig(width=8), seed=20260915).double().cpu()
    values = evaluate_sidis_point_arrays(model, arrays)
    controls = torch.as_tensor(arrays["Gaussian_controls"], dtype=torch.float64)
    replay_error = float(torch.max(torch.abs(values - controls)).detach())

    # Row 1 is the DNN-coupled COMPASS denominator.  Row 2 is a transition
    # numerator and row 3 is fixed-only; both ratios must retain denominator
    # dependence.  The fixed-only ratio is the nontrivial adapter case.
    fixed_only_ratio = values[3] / values[1]
    parameters = tuple(model.parameters())
    gradients = torch.autograd.grad(fixed_only_ratio, parameters)
    gradient = torch.cat([value.detach().ravel() for value in gradients])
    theta = flatten_dnn(model)
    direction = np.sin(np.arange(1, len(theta) + 1, dtype=np.float64))
    direction /= np.linalg.norm(direction)
    analytic = float(gradient @ torch.as_tensor(direction, dtype=torch.float64))
    step = 2.0**-16
    try:
        with torch.no_grad():
            put_dnn(model, theta + step * direction)
            plus_values = evaluate_sidis_point_arrays(model, arrays)
            plus = float((plus_values[3] / plus_values[1]).detach())
            put_dnn(model, theta - step * direction)
            minus_values = evaluate_sidis_point_arrays(model, arrays)
            minus = float((minus_values[3] / minus_values[1]).detach())
    finally:
        put_dnn(model, theta)
    finite_difference = (plus - minus) / (2 * step)
    return {
        "model": "local PyTorch Nested-FiLM width-8 registered Gaussian start",
        "device": "cpu",
        "CUDA_initialized": torch.cuda.is_initialized(),
        "rows": rows,
        "Gaussian_maximum_absolute_replay_error": replay_error,
        "fixed_only_COMPASS_numerator_row": 3,
        "DNN_coupled_COMPASS_denominator_row": 1,
        "fixed_only_ratio": float(fixed_only_ratio.detach()),
        "fixed_only_ratio_gradient_l2": float(torch.linalg.vector_norm(gradient)),
        "directional_derivative_AD": analytic,
        "directional_derivative_FD": finite_difference,
        "directional_derivative_absolute_error": abs(analytic - finite_difference),
        "optimizer_run": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--foundation-root", type=Path, required=True)
    parser.add_argument("--prebuilt-library", type=Path, required=True)
    parser.add_argument("--prebuilt-provenance-receipt", type=Path, required=True)
    parser.add_argument("--arrays-out", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args()
    if args.arrays_out.resolve() == args.receipt_out.resolve():
        raise ValueError("array and receipt outputs must be distinct")
    if args.arrays_out.exists() or args.receipt_out.exists():
        raise ValueError("refuse to overwrite PV17 point-pilot evidence")

    manifest_payload = args.manifest.read_bytes()
    rows = [json.loads(line) for line in manifest_payload.splitlines() if line.strip()]
    hermes, compass = select_pilot_rows(rows)
    pre_inventory = build_inventory(args.foundation_root)
    runtime = load_foundation_read_only(
        args.foundation_root, args.prebuilt_library, args.prebuilt_provenance_receipt
    )

    from work.regional_matching.service import RegionalConfig, RegionalService

    start = time.monotonic()
    results = []
    operators = []
    registered = [("HERMES", hermes), *[("COMPASS", row) for row in compass]]
    services = {}
    try:
        for row in [hermes, compass[0]]:
            key = (row["experiment"], row["detected_hadron"], row["target"])
            target = TARGET_MAP[row["target"]]
            hadron = HADRON_MAP[row["detected_hadron"]]
            target_service = RegionalService(
                RegionalConfig(target=target, hadron=hadron, pdf_xmin=0.003, ff_zmin=0.2)
            )
            proton_service = target_service if target == "proton" else RegionalService(
                RegionalConfig(target="proton", hadron=hadron, pdf_xmin=0.003, ff_zmin=0.2)
            )
            services[key] = (target_service, proton_service)

        for label, row in registered:
            key = (row["experiment"], row["detected_hadron"], row["target"])
            target_service, proton_service = services[key]
            scalar = point_density(target_service, row)
            operator, operator_metadata = build_point_operator(proton_service, target_service, row, scalar)
            validation = None
            if row is hermes or row["normalization"].get("is_fixed_denominator") or scalar["transition_weight"] not in (0.0, 1.0):
                validation = narrow_bin_validation(
                    target_service, row, scalar, relative_width=1e-3
                )
            results.append(
                {
                    "label": label,
                    "selected_index": row["selected_index"],
                    "source_id": row["source_id"],
                    "is_COMPASS_fixed_denominator": bool(
                        row.get("normalization", {}).get("is_fixed_denominator")
                    ),
                    "kinematics": scalar["kinematics"],
                    "transition_weight": scalar["transition_weight"],
                    "nf_hard_and_recoil": scalar["nf_hard_and_recoil"],
                    "nf_OPE_sampled": scalar["nf_OPE_sampled"],
                    "Gaussian_prediction_per_dPhT": scalar["multiplicity_per_dPhT"],
                    "numerical_indicators": scalar["numerical_indicators"],
                    "operator": operator_metadata,
                    "narrow_bin_validation": validation,
                }
            )
            operators.append((operator, operator_metadata))
        for target_service, proton_service in services.values():
            target_service.verify_unchanged()
            if proton_service is not target_service:
                proton_service.verify_unchanged()
    finally:
        for target_service, proton_service in services.values():
            target_service.close()
            if proton_service is not target_service:
                proton_service.close()

    if build_inventory(args.foundation_root) != pre_inventory:
        raise ValueError("foundation regional build inventory changed during read-only pilot")
    arrays = concatenate_operators(operators)
    dnn_replay = replay_current_dnn(arrays)
    args.arrays_out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.arrays_out, **arrays)
    array_manifest = {name: array_receipt(value) for name, value in arrays.items()}
    max_recovery = max(result["operator"]["Gaussian_absolute_recovery_error"] for result in results)
    validations = [result["narrow_bin_validation"] for result in results if result["narrow_bin_validation"]]
    invariants = {
        "one_HERMES_and_complete_22_row_COMPASS_spectrum": len(results) == 23,
        "COMPASS_has_one_denominator_and_21_scored_numerators": sum(
            result["is_COMPASS_fixed_denominator"] for result in results
        ) == 1,
        "all_predictions_finite": all(
            math.isfinite(result["Gaussian_prediction_per_dPhT"]) for result in results
        ),
        "all_predictions_positive": all(
            result["Gaussian_prediction_per_dPhT"] > 0 for result in results
        ),
        "all_Gaussian_operator_recoveries_below_2e_minus_8": max_recovery < 2e-8,
        "current_DNN_Gaussian_replay_below_2e_minus_12": (
            dnn_replay["Gaussian_maximum_absolute_replay_error"] < 2e-12
        ),
        "fixed_only_COMPASS_ratio_gradient_finite_and_nonzero": (
            math.isfinite(dnn_replay["fixed_only_ratio_gradient_l2"])
            and dnn_replay["fixed_only_ratio_gradient_l2"] > 0
        ),
        "fixed_only_COMPASS_ratio_directional_AD_FD_below_2e_minus_8": (
            dnn_replay["directional_derivative_absolute_error"] < 2e-8
        ),
        "narrow_bin_multiplicity_checks_below_2e_minus_3": max(
            item["multiplicity_relative_difference"] for item in validations
        ) < 2e-3,
        "foundation_build_inventory_unchanged": build_inventory(args.foundation_root) == pre_inventory,
    }
    if not all(invariants.values()):
        raise ValueError(f"PV17 SIDIS point-pilot invariant failed: {invariants}")

    receipt = {
        "schema": "pv17-current-regional-sidis-point-pilot-v1",
        "status": "registered_point_operator_pilot_passed_bulk_construction_not_started",
        "source_receipts": {
            "pv17_manifest_sha256": sha256_bytes(manifest_payload),
            "prebuilt_binary_sha256": runtime["binary_sha256"],
            "prebuilt_provenance_receipt_sha256": runtime["provenance_receipt_sha256"],
            "foundation_build_inventory_sha256": sha256_bytes(canonical_json(pre_inventory).encode()),
            "producer_sources": {
                "scripts/run_pv17_sidis_point_pilot.py": sha256_file(Path(__file__)),
                "tmdlab/pv17.py": sha256_file(Path(__file__).resolve().parents[1] / "tmdlab/pv17.py"),
                "tmdlab/models.py": sha256_file(Path(__file__).resolve().parents[1] / "tmdlab/models.py"),
            },
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
        },
        "scope": {
            "HERMES_points": 1,
            "COMPASS_raw_spectrum_rows": 22,
            "COMPASS_scored_numerators": 21,
            "observable": "legacy PV17 dM/dPhT at published average x,z,Q2,PhT",
            "theory": "current regional unprimed N3LL W plus NLO recoil and NLO DIS denominator",
            "production_authorized": False,
            "heavy_threshold_complete": False,
            "GPU_used": False,
            "optimizer_run": False,
        },
        "results": results,
        "arrays": {
            "npz_sha256": sha256_file(args.arrays_out),
            "manifest": array_manifest,
            "operators": len(results),
        },
        "diagnostics": {
            "maximum_Gaussian_operator_recovery_absolute_error": max_recovery,
            "maximum_narrow_bin_multiplicity_relative_difference": max(
                item["multiplicity_relative_difference"] for item in validations
            ),
            "wall_seconds_informational": time.monotonic() - start,
        },
        "current_DNN_CPU_replay": dnn_replay,
        "invariants": invariants,
        "next_gate": (
            "Independently review the point observable and numerical tolerances, then construct "
            "the 7990-row SIDIS operator campaign with resumable per-spectrum receipts."
        ),
    }
    identity_payload = dict(receipt)
    identity_payload["diagnostics"] = dict(receipt["diagnostics"])
    identity_payload["diagnostics"].pop("wall_seconds_informational")
    receipt["identity"] = sha256_bytes(canonical_json(identity_payload).encode())
    args.receipt_out.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_out.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
