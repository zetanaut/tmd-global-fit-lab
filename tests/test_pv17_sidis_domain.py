import math

from scripts.audit_pv17_sidis_domain import (
    OLDER_FIXED_NF_DOMAIN,
    REGIONAL_DOMAIN,
    audit_domain,
    domain_failures,
    point_kinematics,
    region,
)


def _row(source_id, *, experiment="HERMES", x=0.02, z=0.3, Q2=2.56, PhT=0.1,
         scored=True, denominator=False, denominator_source_id=None):
    normalization = {}
    if experiment == "COMPASS":
        normalization = {
            "is_fixed_denominator": denominator,
            "denominator_source_id": denominator_source_id or source_id,
        }
    return {
        "source_id": source_id,
        "selected_by_kinematic_cuts": True,
        "contributes_to_published_point_count": scored,
        "process": "SIDIS",
        "experiment": experiment,
        "target": "deuteron" if experiment == "COMPASS" else "proton",
        "detected_hadron": "piplus",
        "raw": {"x": x, "z": z, "Q2_GeV2": Q2, "PhT_GeV": PhT},
        "normalization": normalization,
    }


def test_regional_domain_accepts_low_q_row_rejected_by_old_fixed_nf_path():
    row = _row("low", x=0.007, Q2=1.5)
    assert domain_failures(row, REGIONAL_DOMAIN) == ()
    assert domain_failures(row, OLDER_FIXED_NF_DOMAIN) == (
        "x_below_min",
        "Q_below_min",
    )


def test_point_kinematics_uses_experiment_flux_and_physical_recoil_map():
    row = _row("h", x=0.1, z=0.5, Q2=4.0, PhT=0.2)
    item = point_kinematics(row)
    assert math.isclose(item["y"], 4.0 / (0.1 * 51.792619266432))
    assert math.isclose(item["qT_over_Q"], 0.2 / 0.5 / 2.0)
    assert item["qT2_GeV2"] < item["finite_recoil_qT2_limit_GeV2"]


def test_compass_ratio_remains_dnn_coupled_through_denominator():
    denominator = _row(
        "den",
        experiment="COMPASS",
        x=0.02,
        z=0.4,
        Q2=4.0,
        PhT=0.08,
        scored=False,
        denominator=True,
    )
    numerator = _row(
        "num",
        experiment="COMPASS",
        x=0.02,
        z=0.4,
        Q2=4.0,
        PhT=0.5,
        denominator_source_id="den",
    )
    assert region(denominator) == "full_additive"
    assert region(numerator) == "FO_only"
    result = audit_domain([denominator, numerator], require_full_population=False)
    assert result["scored_SIDIS_DNN_coupling_after_COMPASS_ratio_map"] == {
        "DNN_coupled": 1,
        "FO_only": 0,
    }
