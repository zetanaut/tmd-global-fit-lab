from scripts.audit_pv17_d0_runii_contract import (
    canonical_sha256,
    crosswalk_d0_rows,
    validate_embedded_hash,
)


def _legacy(index, selected):
    return {
        "experiment": "D0_RunII",
        "selected_by_kinematic_cuts": selected,
        "selected_index": 8276 + index if selected else None,
        "raw": {
            "qT_GeV": 1.1 + index,
            "value": 0.05,
            "statistical_or_published_combined_error": 0.001,
            "systematic_error": 0.002,
        },
    }


def _compiled(index):
    return {
        "candidate_observation_id": f"obs:D0_RUN_2:{index}",
        "source_row_index": index,
        "published_observable": {
            "representative_qT_GeV": 1.1 + index,
            "value": "0.05",
        },
        "support": {"qT": {"low_GeV": float(index), "high_GeV": float(index + 1)}},
        "uncertainty_evidence": {
            "publication_table_components": {
                "statistical_absolute_1_per_GeV": "0.001",
                "systematic_absolute_1_per_GeV": "0.002",
            }
        },
    }


def test_crosswalk_keeps_only_first_eight_without_measurements():
    manifest = [_legacy(index, index < 8) for index in range(23)]
    plan = {"compiled_rows": [_compiled(index) for index in range(23)]}
    crosswalk, checks = crosswalk_d0_rows(manifest, plan)
    assert all(checks.values())
    assert [row["candidate_observation_id"] for row in crosswalk] == [
        f"obs:D0_RUN_2:{index}" for index in range(8)
    ]
    assert all("value" not in row and "error" not in row for row in crosswalk)


def test_embedded_canonical_hash_validation():
    payload = {"a": 1, "b": [2, 3]}
    value = {**payload, "digest": canonical_sha256(payload)}
    assert validate_embedded_hash(value, "digest")
    value["a"] = 4
    assert not validate_embedded_hash(value, "digest")
