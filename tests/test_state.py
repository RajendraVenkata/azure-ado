from ado_migrate.state import StateStore


def test_state_persists_completion_and_id_mapping_across_reload(tmp_path):
    state_path = tmp_path / "state.json"

    store = StateStore(str(state_path))
    store.mark_complete("repos", source_id="repo-1", destination_id="dest-repo-1")
    store.save()

    reloaded = StateStore(str(state_path))
    reloaded.load()

    assert reloaded.is_complete("repos", source_id="repo-1") is True
    assert reloaded.get_destination_id("repos", source_id="repo-1") == "dest-repo-1"


def test_state_unmigrated_item_is_not_complete(tmp_path):
    state_path = tmp_path / "state.json"

    store = StateStore(str(state_path))

    assert store.is_complete("repos", source_id="never-migrated") is False
    assert store.get_destination_id("repos", source_id="never-migrated") is None


def test_state_load_on_missing_file_starts_empty(tmp_path):
    state_path = tmp_path / "does-not-exist.json"

    store = StateStore(str(state_path))
    store.load()

    assert store.is_complete("repos", source_id="repo-1") is False


def test_state_list_destination_ids_returns_all_completed_mappings_for_type(tmp_path):
    store = StateStore(str(tmp_path / "state.json"))
    store.mark_complete("area_paths", source_id="Team A", destination_id="Team A (dest)")
    store.mark_complete("area_paths", source_id="Team B", destination_id="Team B (dest)")
    store.mark_complete("repos", source_id="repo-1", destination_id="repo-9")

    assert store.list_destination_ids("area_paths") == {
        "Team A": "Team A (dest)",
        "Team B": "Team B (dest)",
    }


def test_state_list_destination_ids_empty_for_unknown_type(tmp_path):
    store = StateStore(str(tmp_path / "state.json"))

    assert store.list_destination_ids("area_paths") == {}


def test_state_records_and_persists_failures_across_reload(tmp_path):
    state_path = tmp_path / "state.json"

    store = StateStore(str(state_path))
    store.record_failure("work_items", "boom: rate limit exceeded")
    store.save()

    reloaded = StateStore(str(state_path))
    reloaded.load()

    assert reloaded.get_failures("work_items") == ["boom: rate limit exceeded"]


def test_state_get_failures_empty_for_type_with_no_failures(tmp_path):
    store = StateStore(str(tmp_path / "state.json"))

    assert store.get_failures("work_items") == []
