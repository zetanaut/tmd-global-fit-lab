import math

from scripts.run_pv17_sidis_point_pilot import (
    multiplicity_from_pieces,
    observable_scale,
    transition_weight,
)


def test_transition_weight_has_current_endpoints_and_smooth_midpoint():
    assert transition_weight(0.0) == 1.0
    assert transition_weight(0.15) == 1.0
    assert math.isclose(transition_weight(0.225), 0.5, rel_tol=0.0, abs_tol=1e-15)
    assert transition_weight(0.30) == 0.0
    assert transition_weight(2.0) == 0.0


def test_legacy_point_observable_uses_dphT_jacobian_once():
    scale = observable_scale(x=0.1, z=0.5, PhT=0.2, y=0.4, F2=2.0, FL=0.1)
    Y = 1 + (1 - 0.4) ** 2
    assert math.isclose(scale, 2 * 0.2 * 0.1 / (0.5**2 * (Y * 2.0 - 0.4**2 * 0.1)))


def test_multiplicity_assembles_transverse_and_longitudinal_pieces():
    inputs = dict(x=0.1, z=0.5, PhT=0.2, y=0.4, F2=2.0, FL=0.1)
    value = multiplicity_from_pieces(
        **inputs, f_W=3.0, FO_T=0.4, FO_L=0.2, f_ASY=0.1
    )
    Y = 1 + (1 - inputs["y"]) ** 2
    expected = observable_scale(**inputs) * (Y * (3.0 + 0.4 - 0.1) + 2 * 0.6 * 0.2)
    assert math.isclose(value, expected)
