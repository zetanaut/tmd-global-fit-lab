import math

import pytest

from scripts.reevaluate_full_compass import (
    cubic_smoothstep,
    paper_factorization_fraction,
    parse_binned_qualifier,
    support_domain,
)


def test_parse_binned_qualifier_accepts_hepdata_formats():
    assert parse_binned_qualifier("2e+01 (BIN=2e+01 TO 8e+01)") == (20.0, 20.0, 80.0)
    assert parse_binned_qualifier("0.157 (BIN= 0.1 TO 0.21)") == (0.157, 0.1, 0.21)


def test_parse_binned_qualifier_rejects_missing_or_bad_support():
    with pytest.raises(ValueError):
        parse_binned_qualifier("0.44")
    with pytest.raises(ValueError):
        parse_binned_qualifier("0.2 (BIN=0.3 TO 0.1)")


def test_paper_envelope_matches_declared_parameters():
    assert cubic_smoothstep(-1.0) == 0.0
    assert cubic_smoothstep(0.5) == 0.5
    assert cubic_smoothstep(2.0) == 1.0
    assert paper_factorization_fraction(0.10) == 0.0
    assert math.isclose(paper_factorization_fraction(0.15), 1.125)
    assert math.isclose(paper_factorization_fraction(0.20), 2.0)
    assert math.isclose(paper_factorization_fraction(0.25), 3.125)


def test_support_domains_use_full_bin_extrema():
    assert support_domain(0.02, 0.15) == "pure_tmd_core"
    assert support_domain(0.10, 0.20) == "matched_transition_or_mixed"
    assert support_domain(0.30, 0.80) == "pure_fixed_order_validation"
    with pytest.raises(ValueError):
        support_domain(0.4, 0.2)
