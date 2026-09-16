import math

import numpy as np

from scripts.build_pv17_metric_contract import build_metric_arrays


def _row(
    source_id,
    selected_index,
    point_index,
    process,
    experiment,
    raw,
    transformed,
    normalization,
    *,
    scored=True,
):
    return {
        "source_id": source_id,
        "selected_by_kinematic_cuts": True,
        "contributes_to_published_point_count": scored,
        "selected_index": selected_index,
        "published_point_index": point_index if scored else None,
        "process": process,
        "experiment": experiment,
        "raw": raw,
        "transformed": transformed,
        "normalization": normalization,
    }


def test_compass_shared_denominator_is_off_diagonal_response():
    denominator = _row(
        "denominator",
        1,
        None,
        "SIDIS",
        "COMPASS",
        dict(value=4.0, statistical_error=0.4, systematic_error=0.8),
        dict(value=1.0, statistical_error=math.sqrt(0.02), systematic_error=math.sqrt(0.08)),
        dict(group="g", denominator_source_id="denominator", is_fixed_denominator=True),
        scored=False,
    )
    numerators = []
    for selected_index, point_index, value, stat, syst in (
        (2, 1, 2.0, 0.2, 0.3),
        (3, 2, 3.0, 0.3, 0.4),
    ):
        ratio = value / 4.0
        transformed_stat = ratio * math.sqrt((stat / value) ** 2 + (0.4 / 4.0) ** 2)
        transformed_syst = ratio * math.sqrt((syst / value) ** 2 + (0.8 / 4.0) ** 2)
        numerators.append(
            _row(
                f"n{point_index}",
                selected_index,
                point_index,
                "SIDIS",
                "COMPASS",
                dict(value=value, statistical_error=stat, systematic_error=syst),
                dict(
                    value=ratio,
                    statistical_error=transformed_stat,
                    systematic_error=transformed_syst,
                ),
                dict(group="g", denominator_source_id="denominator", is_fixed_denominator=False),
            )
        )

    arrays, metadata = build_metric_arrays(
        [denominator, *numerators], require_full_population=False
    )
    assert np.array_equal(arrays["data"], [0.5, 0.75])
    expected_diagonal = np.asarray([(0.2**2 + 0.3**2) / 16, (0.3**2 + 0.4**2) / 16])
    assert np.allclose(arrays["diagonal_variance"], expected_diagonal)
    u = arrays["COMPASS_denominator_responses"][:, 0]
    expected_u = np.asarray([0.5, 0.75]) * math.sqrt(0.4**2 + 0.8**2) / 4.0
    assert np.allclose(u, expected_u)
    covariance = np.diag(expected_diagonal) + np.outer(expected_u, expected_u)
    assert covariance[0, 1] > 0
    assert metadata["invariants"]["COMPASS_marginals_reproduce_published_propagation"]


def test_dy_normalization_is_t0_pattern_not_data_diagonal():
    value, stat, fraction = 2.0, 0.1, 0.25
    row = _row(
        "dy",
        1,
        1,
        "DY",
        "E288_200",
        dict(value=value, statistical_error=stat),
        dict(value=value, total_diagonal_error=math.hypot(stat, fraction * value)),
        dict(rule="identity", group=None),
    )
    arrays, metadata = build_metric_arrays([row], require_full_population=False)
    assert arrays["diagonal_variance"][0] == stat**2
    assert arrays["normalization_fraction_patterns"][0, 0] == fraction
    assert metadata["invariants"]["DY_Z_marginals_at_t0_equal_data_reproduce_legacy_diagonal"]


def test_z_fixed_theory_factor_does_not_enter_metric_arrays():
    value, stat, luminosity = 10.0, 0.5, 0.039
    row = _row(
        "z",
        1,
        1,
        "Z",
        "CDF_RunI",
        dict(value=value, statistical_or_published_combined_error=stat),
        dict(
            value=value,
            statistical_or_published_combined_error=stat,
            systematic_error=0.0,
            total_diagonal_error=math.hypot(stat, luminosity * value),
        ),
        dict(rule="fixed_theory_normalization_factor", factor=1.114, group=None),
    )
    arrays, _ = build_metric_arrays([row], require_full_population=False)
    assert arrays["data"][0] == value
    assert arrays["diagonal_variance"][0] == stat**2
    assert np.count_nonzero(arrays["normalization_fraction_patterns"]) == 1
    assert math.isclose(arrays["normalization_fraction_patterns"][0, 4], luminosity)


def test_d0_run_ii_keeps_published_normalized_shape_not_PV17_theory_conversion():
    row = _row(
        "d0ii",
        1,
        1,
        "Z",
        "D0_RunII",
        dict(
            value=0.0532,
            statistical_or_published_combined_error=0.0013,
            systematic_error=0.0024,
        ),
        dict(
            value=13.60856,
            statistical_error=0.33254,
            systematic_error=0.61392,
            total_diagonal_error=1.12995851764567,
            integrated_sigma_Z_pb=255.8,
        ),
        dict(rule="convert_normalized_shape_with_PV17_theory", group=None),
    )
    arrays, metadata = build_metric_arrays([row], require_full_population=False)
    assert arrays["data"][0] == 0.0532
    assert math.isclose(
        arrays["diagonal_variance"][0], 0.0013**2 + 0.0024**2
    )
    assert np.count_nonzero(arrays["normalization_fraction_patterns"]) == 0
    assert metadata["invariants"][
        "D0_RunII_uses_raw_normalized_shape_without_PV17_theory_factor"
    ]
