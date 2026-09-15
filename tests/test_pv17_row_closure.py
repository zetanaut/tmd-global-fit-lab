import math

from scripts.audit_pv17_row_closure import (
    apply_compass_normalization,
    dy_cut_checks,
    numeric_rows,
    sidis_cut_checks,
    strict_bin_index,
)


def test_numeric_rows_obeys_header_and_field_contract():
    payload = b"header\nignored words\n 1 2D+00 3 4\n 2 5 6 7\n"
    assert numeric_rows(payload, skip_lines=1, fields=4) == [
        (3, [1.0, 2.0, 3.0, 4.0]),
        (4, [2.0, 5.0, 6.0, 7.0]),
    ]


def test_sidis_cuts_are_strict_at_published_boundaries():
    assert all(sidis_cut_checks(2.0, 0.3, 0.1, 0.2).values())
    assert not sidis_cut_checks(1.4, 0.3, 0.1, 0.2)["Q2_gt_1p4_GeV2"]
    assert not sidis_cut_checks(2.0, 0.2, 0.1, 0.2)["z_gt_0p2"]
    assert not sidis_cut_checks(2.0, 0.74, 0.1, 0.2)["z_lt_0p74"]
    q_limit = 0.2 * math.sqrt(2.0) + 0.5
    assert not sidis_cut_checks(2.0, 0.3, q_limit, 0.2)["PhT_lt_0p2Q_plus_0p5_GeV"]


def test_dy_windows_and_inclusive_qt_boundary():
    assert all(dy_cut_checks(3, 12.0, 2.9).values())
    assert not dy_cut_checks(4, 12.0, 2.9)["historical_mass_window"]
    assert all(dy_cut_checks(6, 11.0, 2.7).values())
    assert not dy_cut_checks(6, 9.5, 1.0)["historical_mass_window"]


def test_strict_bin_index_preserves_open_intervals():
    bins = ((0.0, 1.0), (1.0, 2.0))
    assert strict_bin_index(0.5, bins) == 0
    assert strict_bin_index(1.5, bins) == 1
    assert strict_bin_index(1.0, bins) is None


def test_compass_normalization_marks_one_fixed_constraint_per_spectrum(monkeypatch):
    rows = []
    for index, (value, stat, syst, pht) in enumerate(
        ((4.0, 0.4, 0.8, 0.1), (2.0, 0.2, 0.3, 0.2)), start=1
    ):
        rows.append(
            {
                "source_id": f"synthetic:{index}",
                "selected_by_kinematic_cuts": True,
                "contributes_to_published_point_count": True,
                "raw": {
                    "value": value,
                    "statistical_error": stat,
                    "systematic_error": syst,
                    "Q2_GeV2": 2.0,
                    "x": 0.01,
                    "z": 0.3,
                    "PhT_GeV": pht,
                },
            }
        )
    monkeypatch.setattr(
        "scripts.audit_pv17_row_closure.compass_bin_key", lambda row: (0, 0, 0)
    )
    assert apply_compass_normalization(rows, "piplus") == 1
    assert rows[0]["normalization"]["is_fixed_denominator"] is True
    assert rows[0]["contributes_to_published_point_count"] is False
    assert rows[1]["contributes_to_published_point_count"] is True
    assert rows[1]["transformed"]["value"] == 0.5
    assert math.isclose(rows[1]["transformed"]["statistical_error"], math.sqrt(0.005))
