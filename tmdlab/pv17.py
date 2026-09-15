"""Compact PV17 SIDIS point-operator validation and PyTorch contraction.

The point operators already include the legacy ``dM/dPhT`` observable scale.
Rows may have no W entries when the current matching transition is exactly
zero; their prediction is then the stored fixed contribution.  Keeping those
rows empty is intentional and avoids inventing inactive flavor channels.
"""

from __future__ import annotations

import numpy as np
import torch


def validate_sidis_point_arrays(arrays: dict[str, np.ndarray]) -> int:
    required = {
        "coordinates",
        "weights",
        "point_index",
        "species1",
        "species2",
        "active_nf",
        "nucleon",
        "struck_pid",
        "coordinate_offsets",
        "weight_offsets",
        "fixed_predictions",
        "Gaussian_controls",
    }
    if set(arrays) != required:
        raise ValueError("unexpected PV17 SIDIS point-operator array schema")
    if not all(isinstance(value, np.ndarray) and np.isfinite(value).all()
               for value in arrays.values()):
        raise ValueError("finite NumPy PV17 SIDIS point-operator arrays required")

    coordinates = arrays["coordinates"]
    weights = arrays["weights"]
    point_index = arrays["point_index"]
    coordinate_offsets = arrays["coordinate_offsets"]
    weight_offsets = arrays["weight_offsets"]
    fixed = arrays["fixed_predictions"]
    controls = arrays["Gaussian_controls"]
    rows = len(fixed)

    if coordinates.ndim != 2 or coordinates.shape[1] != 4 or weights.ndim != 1:
        raise ValueError("invalid PV17 point coordinate or weight shape")
    if controls.shape != fixed.shape or coordinate_offsets.shape != (rows + 1,) \
            or weight_offsets.shape != (rows + 1,):
        raise ValueError("invalid PV17 point row-offset shape")
    integer_names = (
        "point_index", "species1", "species2", "active_nf", "nucleon",
        "struck_pid", "coordinate_offsets", "weight_offsets",
    )
    if any(not np.issubdtype(arrays[name].dtype, np.integer) for name in integer_names):
        raise ValueError("integer PV17 point axes required")
    if any(arrays[name].shape != weights.shape for name in
           ("point_index", "species1", "species2", "nucleon", "struck_pid")):
        raise ValueError("PV17 signed-channel axes must match weights")
    if arrays["active_nf"].shape != (len(coordinates),):
        raise ValueError("one active-flavor label per PV17 coordinate required")
    if coordinate_offsets[0] != 0 or coordinate_offsets[-1] != len(coordinates) \
            or weight_offsets[0] != 0 or weight_offsets[-1] != len(weights) \
            or np.any(np.diff(coordinate_offsets) < 0) or np.any(np.diff(weight_offsets) < 0):
        raise ValueError("invalid PV17 point offsets")
    if np.any((coordinates[:, 0] < 0) | (coordinates[:, 1] <= 0)
              | (coordinates[:, 1] >= 1) | (coordinates[:, 2] <= 0)
              | (coordinates[:, 2] >= 1) | (coordinates[:, 3] <= 0)):
        raise ValueError("invalid PV17 point coordinates")
    if np.any((arrays["species1"] < 0) | (arrays["species1"] >= 10)) \
            or np.any((arrays["species2"] < 0) | (arrays["species2"] >= 30)):
        raise ValueError("invalid PV17 point species map")
    if len(point_index) and (point_index.min() < 0 or point_index.max() >= len(coordinates)):
        raise ValueError("PV17 point index outside coordinate support")

    for row in range(rows):
        lo, hi = weight_offsets[row:row + 2]
        clo, chi = coordinate_offsets[row:row + 2]
        if hi > lo and (point_index[lo:hi].min() < clo or point_index[lo:hi].max() >= chi):
            raise ValueError("PV17 point channel crosses row coordinate support")
        if hi == lo and chi != clo:
            raise ValueError("PV17 point row has unused coordinates")
    return rows


def evaluate_sidis_point_arrays(model, arrays: dict[str, np.ndarray], *, device="cpu"):
    """Return differentiable raw ``dM/dPhT`` values in operator row order."""
    rows = validate_sidis_point_arrays(arrays)
    parameter = next(model.parameters())
    target = torch.device(device)
    if parameter.device != target or parameter.dtype != torch.float64:
        raise ValueError("model must already be float64 on the requested device")

    fixed = torch.as_tensor(arrays["fixed_predictions"], dtype=torch.float64, device=target)
    if not len(arrays["weights"]):
        return fixed
    coordinates = torch.as_tensor(arrays["coordinates"], dtype=torch.float64, device=target)
    point_index = torch.as_tensor(arrays["point_index"], dtype=torch.int64, device=target)
    selected = coordinates[point_index]
    species1 = torch.as_tensor(arrays["species1"], dtype=torch.int64, device=target)
    species2 = torch.as_tensor(arrays["species2"], dtype=torch.int64, device=target)
    log_product = (
        model.incoming.log_multiplier(selected[:, 0], selected[:, 1], species1)
        + model.outgoing.log_multiplier(selected[:, 0], selected[:, 2], species2)
        + 2 * model.cs(selected[:, 0]) * torch.log(selected[:, 3] / model.Qref)
    )
    products = torch.exp(log_product)
    if not torch.isfinite(products).all():
        raise ValueError("nonfinite PV17 SIDIS point products")
    weights = torch.as_tensor(arrays["weights"], dtype=torch.float64, device=target)
    counts = torch.as_tensor(
        np.diff(arrays["weight_offsets"]), dtype=torch.int64, device=target
    )
    row_index = torch.repeat_interleave(torch.arange(rows, device=target), counts)
    variable = torch.zeros(rows, dtype=torch.float64, device=target)
    variable.scatter_add_(0, row_index, weights * products)
    values = fixed + variable
    if not torch.isfinite(values).all():
        raise ValueError("nonfinite PV17 SIDIS point predictions")
    return values
