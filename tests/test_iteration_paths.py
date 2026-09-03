from ado_migrate.client import InMemoryFakeAdoClient, IterationPath
from ado_migrate.paths import migrate_iteration_paths
from ado_migrate.state import StateStore


def test_migrate_iteration_paths_preserves_dates_on_empty_destination(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_iteration_paths(
        "SourceProject",
        [IterationPath(path="Sprint 1", start_date="2026-01-01", end_date="2026-01-14")],
    )
    state = StateStore(str(tmp_path / "state.json"))

    section = migrate_iteration_paths(
        source, dest, "SourceProject", "DestProject", state
    )

    assert dest.list_iteration_paths("DestProject") == [
        IterationPath(path="Sprint 1", start_date="2026-01-01", end_date="2026-01-14")
    ]
    assert state.is_complete("iteration_paths", source_id="Sprint 1")
    assert state.get_destination_id("iteration_paths", source_id="Sprint 1") == "Sprint 1"
    assert "Sprint 1" in section.items


def test_migrate_iteration_paths_creates_parents_before_children(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_iteration_paths(
        "SourceProject",
        [
            IterationPath(path="Release 1/Sprint 1"),
            IterationPath(path="Release 1"),
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))

    migrate_iteration_paths(source, dest, "SourceProject", "DestProject", state)

    assert [p.path for p in dest.list_iteration_paths("DestProject")] == [
        "Release 1",
        "Release 1/Sprint 1",
    ]


def test_migrate_iteration_paths_does_not_duplicate_path_already_on_destination(
    tmp_path,
):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_iteration_paths(
        "SourceProject",
        [IterationPath(path="Sprint 1"), IterationPath(path="Sprint 2")],
    )
    dest.seed_iteration_paths("DestProject", [IterationPath(path="Sprint 1")])
    state = StateStore(str(tmp_path / "state.json"))

    migrate_iteration_paths(source, dest, "SourceProject", "DestProject", state)

    assert len(dest.mutation_log) == 1
    assert "Sprint 2" in dest.mutation_log[0].description


def test_migrate_iteration_paths_rerun_makes_no_additional_mutating_calls(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_iteration_paths("SourceProject", [IterationPath(path="Sprint 1")])
    state = StateStore(str(tmp_path / "state.json"))

    migrate_iteration_paths(source, dest, "SourceProject", "DestProject", state)
    calls_after_first_run = len(dest.mutation_log)

    migrate_iteration_paths(source, dest, "SourceProject", "DestProject", state)

    assert len(dest.mutation_log) == calls_after_first_run


def test_migrate_iteration_paths_dry_run_reports_without_mutating(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=True)
    source.seed_iteration_paths("SourceProject", [IterationPath(path="Sprint 1")])
    state = StateStore(str(tmp_path / "state.json"))

    section = migrate_iteration_paths(
        source, dest, "SourceProject", "DestProject", state
    )

    assert section.items == ["Sprint 1"]
    assert dest.list_iteration_paths("DestProject") == []
    assert state.is_complete("iteration_paths", source_id="Sprint 1") is False
