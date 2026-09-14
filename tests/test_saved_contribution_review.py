import importlib.util
from pathlib import Path
import numpy as np
import pytest

spec = importlib.util.spec_from_file_location('saved_review', Path(__file__).resolve().parents[1]/'scripts/review_w8_saved.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


def test_fixed_split_uses_fixed_sigma_and_preserves_signed_contributions():
    result = review.fixed_split(np.array([3.,1.]), np.array([1.,3.]), np.array([2.,4.]))
    np.testing.assert_array_equal(result, [1.,-.5])


@pytest.mark.parametrize('sigma', [np.array([0.,1.]), np.array([np.nan,1.])])
def test_fixed_split_rejects_invalid_normalization(sigma):
    with pytest.raises(ValueError):
        review.fixed_split(np.ones(2), np.zeros(2), sigma)


def test_fixed_split_rejects_broadcasting():
    with pytest.raises(ValueError):
        review.fixed_split(np.ones(2), np.zeros(1), np.ones(2))
