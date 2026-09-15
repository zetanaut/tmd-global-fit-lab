import hashlib

import numpy as np

from scripts.audit_pv17_sidis_endpoint import (
    canonical_json,
    grouped_summaries,
    nonpositive_rows,
    numeric_summary,
    shard_receipt_identity_valid,
)


def records():
    return [
        {
            "selected_index": 3,
            "experiment": "HERMES",
            "target": "proton",
            "detected_hadron": "kminus",
            "transition_weight": 1.0,
            "qT_over_Q": 0.1,
        },
        {
            "selected_index": 8,
            "experiment": "COMPASS",
            "target": "deuteron",
            "detected_hadron": "piplus",
            "transition_weight": 0.0,
            "qT_over_Q": 0.5,
        },
    ]


def test_endpoint_summary_preserves_nonpositive_row_identity_and_role():
    values = np.array([-0.25, 2.0])
    assert numeric_summary(values) == {
        "rows": 2,
        "minimum": -0.25,
        "maximum": 2.0,
        "nonpositive": 1,
    }
    assert nonpositive_rows(records(), values) == [
        {
            "selected_index": 3,
            "experiment": "HERMES",
            "target": "proton",
            "hadron": "kminus",
            "matching_role": "full_additive",
            "qT_over_Q": 0.1,
            "prediction": -0.25,
        }
    ]


def test_grouped_summary_uses_receipt_labels():
    grouped = grouped_summaries(records(), np.array([-0.25, 2.0]), "experiment")
    assert grouped["HERMES"]["nonpositive"] == 1
    assert grouped["COMPASS"]["minimum"] == 2.0


def test_shard_identity_omits_only_informational_wall_time():
    receipt = {"diagnostics": {"wall_seconds_informational": 2.0, "error": 0.0}}
    receipt["identity"] = hashlib.sha256(
        canonical_json({"diagnostics": {"error": 0.0}}).encode("utf-8")
    ).hexdigest()
    assert shard_receipt_identity_valid(receipt)
    receipt["diagnostics"]["error"] = 1.0
    assert not shard_receipt_identity_valid(receipt)
