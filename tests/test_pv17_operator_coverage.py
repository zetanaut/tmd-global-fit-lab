from scripts.audit_pv17_operator_coverage import (
    BLOCKED_D0_RUN_II_STATUS,
    coverage_status,
    geometry_key_for_current,
    geometry_key_for_pv17,
)


def test_fixed_target_geometry_key_includes_q_and_qt():
    current = {
        "dataset_id": "DY:E288_400",
        "kinematics": {"QM": 5.5, "qT": 0.3},
    }
    pv17 = {
        "experiment": "E288_400",
        "process": "DY",
        "raw": {"Q_GeV": 5.5, "qT_GeV": 0.3},
    }
    assert geometry_key_for_current(current) == geometry_key_for_pv17(pv17)


def test_z_geometry_key_uses_dataset_and_qt_not_nominal_q_rounding():
    current = {
        "dataset_id": "DY:CDF_RUN_1",
        "kinematics": {"QM": 91.0, "qT": 0.25},
    }
    pv17 = {
        "experiment": "CDF_RunI",
        "process": "Z",
        "raw": {"Q_GeV": 91.1876, "qT_GeV": 0.25},
    }
    assert geometry_key_for_current(current) == geometry_key_for_pv17(pv17)


def test_d0_run_ii_is_not_treated_as_an_absolute_operator_gap():
    row = {"process": "Z", "experiment": "D0_RunII"}
    prepared = {"observation_id": "obs:D0_RUN_2:0"}
    assert coverage_status(row, prepared, {}) == BLOCKED_D0_RUN_II_STATUS
