import numpy as np

from scripts.audit_pv17_hermes_kminus_sign import (
    matching_role,
    observable_components,
    sign,
    validate_flavor_map,
)


def test_observable_components_preserve_matching_signs():
    scalar = {
        "kinematics": {"x": 0.2, "z": 0.4, "PhT": 0.1, "y": 0.3},
        "inclusive_DIS": {"F2": 0.5, "FL": 0.1},
        "pieces_per_dqT2": {"f_W": -0.2, "FO_T": 0.3, "FO_L": 0.04, "f_ASY": 0.5},
    }
    pieces = observable_components(scalar)
    assert pieces["W"] < 0
    assert pieces["FO_T"] > 0
    assert pieces["FO_L"] > 0
    assert pieces["minus_switched_ASY"] < 0


def test_matching_role_and_sign_are_exact_at_boundaries():
    assert [matching_role(value) for value in (0.0, 0.5, 1.0)] == [
        "FO_only", "transition", "full_additive"
    ]
    assert [sign(value) for value in (-1.0, 0.0, 1.0)] == [-1, 0, 1]


def test_Kminus_charge_conjugation_and_neutron_incoming_map():
    incoming = {-2: 0, -1: 1, 1: 2, 2: 3}
    outgoing = {
        ("K+", -2): 4,
        ("K+", 2): 5,
        ("K+", -1): 6,
        ("K+", 1): 7,
    }

    def neutron(pid):
        return {1: 2, 2: 1, -1: -2, -2: -1}[pid]

    arrays = {
        "weight_offsets": np.array([0, 4]),
        "struck_pid": np.array([2, -2, 1, -1]),
        "nucleon": np.array([0, 0, 1, 1]),
        "species1": np.array([3, 0, 3, 0]),
        "species2": np.array([4, 5, 6, 7]),
    }
    assert validate_flavor_map(
        arrays, 0, "deuteron", incoming=incoming, outgoing=outgoing, neutron=neutron
    ) == 4
