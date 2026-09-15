import numpy as np
import pytest
import torch

from tmdlab.models import Config, build
from tmdlab.pv17 import evaluate_sidis_point_arrays, validate_sidis_point_arrays


def example_arrays():
    return {
        "coordinates": np.asarray([[1.0, 0.2, 0.3, 2.0]], dtype=np.float64),
        "weights": np.asarray([0.4], dtype=np.float64),
        "point_index": np.asarray([0], dtype=np.int64),
        "species1": np.asarray([0], dtype=np.int64),
        "species2": np.asarray([0], dtype=np.int64),
        "active_nf": np.asarray([3], dtype=np.int8),
        "nucleon": np.asarray([0], dtype=np.int8),
        "struck_pid": np.asarray([1], dtype=np.int8),
        "coordinate_offsets": np.asarray([0, 1, 1], dtype=np.int64),
        "weight_offsets": np.asarray([0, 1, 1], dtype=np.int64),
        "fixed_predictions": np.asarray([0.2, 0.6], dtype=np.float64),
        "Gaussian_controls": np.asarray([0.2 + 0.4 * np.exp(-0.25), 0.6]),
    }


def test_point_operator_supports_fixed_only_rows_and_ratio_gradient():
    arrays = example_arrays()
    assert validate_sidis_point_arrays(arrays) == 2
    model = build(Config(width=8), seed=20260915).double().cpu()
    values = evaluate_sidis_point_arrays(model, arrays)
    assert torch.allclose(
        values, torch.as_tensor(arrays["Gaussian_controls"]), atol=2e-15, rtol=0.0
    )
    ratio = values[1] / values[0]
    gradient = torch.autograd.grad(ratio, model.incoming.raw_widths)[0]
    assert torch.isfinite(gradient).all()
    assert torch.count_nonzero(gradient) > 0


def test_point_operator_rejects_cross_row_indices():
    arrays = example_arrays()
    arrays["coordinate_offsets"] = np.asarray([0, 0, 1], dtype=np.int64)
    with pytest.raises(ValueError, match="crosses row"):
        validate_sidis_point_arrays(arrays)
