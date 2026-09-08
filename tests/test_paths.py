from ado_migrate.client import InMemoryFakeAdoClient
from ado_migrate.paths import migrate_area_paths
from ado_migrate.state import StateStore


def test_migrate_area_paths_creates_single_path_on_empty_destination(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_area_paths("SourceProject", ["Team A"])
    state = StateStore(str(tmp_path / "state.json"))

    section = migrate_area_paths(source, dest, "SourceProject", "DestProject", state)

    assert dest.list_area_paths("DestProject") == ["Team A"]
    assert state.is_complete("area_paths", source_id="Team A")
    assert state.get_destination_id("area_paths", source_id="Team A") == "Team A"
    assert "Team A" in section.items


def test_migrate_area_paths_creates_parents_before_children(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_area_paths("SourceProject", ["Team A/Sub Team", "Team A"])
    state = StateStore(str(tmp_path / "state.json"))

    migrate_area_paths(source, dest, "SourceProject", "DestProject", state)

    assert dest.list_area_paths("DestProject") == ["Team A", "Team A/Sub Team"]


def test_migrate_area_paths_does_not_duplicate_path_already_on_destination(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_area_paths("SourceProject", ["Team A", "Team B"])
    dest.seed_area_paths("DestProject", ["Team A"])
    state = StateStore(str(tmp_path / "state.json"))

    section = migrate_area_paths(source, dest, "SourceProject", "DestProject", state)

    assert dest.list_area_paths("DestProject") == ["Team A", "Team B"]
    assert len(dest.mutation_log) == 1
    assert "Team B" in dest.mutation_log[0].description
    assert state.is_complete("area_paths", source_id="Team A")
    assert state.is_complete("area_paths", source_id="Team B")
    assert set(section.items) == {"Team A", "Team B"}


def test_migrate_area_paths_rerun_makes_no_additional_mutating_calls(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_area_paths("SourceProject", ["Team A"])
    state = StateStore(str(tmp_path / "state.json"))

    migrate_area_paths(source, dest, "SourceProject", "DestProject", state)
    calls_after_first_run = len(dest.mutation_log)

    section = migrate_area_paths(source, dest, "SourceProject", "DestProject", state)

    assert len(dest.mutation_log) == calls_after_first_run
    assert section.items == ["Team A"]


def test_migrate_area_paths_recreates_path_deleted_from_destination(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_area_paths("SourceProject", ["Team A"])
    state = StateStore(str(tmp_path / "state.json"))

    migrate_area_paths(source, dest, "SourceProject", "DestProject", state)
    dest._area_paths["DestProject"] = []

    section = migrate_area_paths(source, dest, "SourceProject", "DestProject", state)

    assert dest.list_area_paths("DestProject") == ["Team A"]
    assert section.items == ["Team A"]


def test_migrate_area_paths_dry_run_reports_without_mutating(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=True)
    source.seed_area_paths("SourceProject", ["Team A"])
    state = StateStore(str(tmp_path / "state.json"))

    section = migrate_area_paths(source, dest, "SourceProject", "DestProject", state)

    assert section.items == ["Team A"]
    assert dest.list_area_paths("DestProject") == []
    assert state.is_complete("area_paths", source_id="Team A") is False
