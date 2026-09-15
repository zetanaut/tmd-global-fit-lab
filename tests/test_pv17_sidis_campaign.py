from scripts.build_pv17_sidis_point_operators import plan_shards, source_table


def row(index, experiment, source, group=None):
    return {
        "selected_by_kinematic_cuts": True,
        "process": "SIDIS",
        "selected_index": index,
        "experiment": experiment,
        "source_id": source,
        "normalization": {"group": group},
    }


def test_source_table_removes_only_line_binding():
    assert source_table("git:commit:path/to/file.dat:line17") == "git:commit:path/to/file.dat"


def test_campaign_shards_HERMES_by_table_and_COMPASS_by_complete_spectrum():
    rows = [
        row(3, "COMPASS", "git:c:compass.dat:line3", "spectrum-b"),
        row(1, "HERMES", "git:c:hermes.dat:line1"),
        row(2, "HERMES", "git:c:hermes.dat:line2"),
        row(4, "COMPASS", "git:c:compass.dat:line4", "spectrum-b"),
        row(5, "COMPASS", "git:c:compass.dat:line5", "spectrum-c"),
    ]
    shards = plan_shards(rows)
    assert [item["kind"] for item in shards] == [
        "HERMES_source_table", "COMPASS_spectrum", "COMPASS_spectrum"
    ]
    assert [item["selected_indices"] for item in shards] == [[1, 2], [3, 4], [5]]
