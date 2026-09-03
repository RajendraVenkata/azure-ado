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
