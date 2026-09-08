from ado_migrate.client import InMemoryFakeAdoClient, Query
from ado_migrate.queries import migrate_queries
from ado_migrate.state import StateStore


def test_migrate_queries_rewrites_area_and_iteration_path_literals(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_queries(
        "SourceProject",
        [
            Query(
                id="q-1",
                name="My Active Bugs",
                folder_path="Shared Queries/Team A",
                wiql=(
                    "SELECT [System.Id] FROM WorkItems WHERE "
                    "[System.AreaPath] = 'Team A' AND "
                    "[System.IterationPath] UNDER 'Sprint 1'"
                ),
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))
    state.mark_complete("area_paths", source_id="Team A", destination_id="Team A (dest)")
    state.mark_complete(
        "iteration_paths", source_id="Sprint 1", destination_id="Sprint 1 (dest)"
    )

    section = migrate_queries(source, dest, "SourceProject", "DestProject", state)

    dest_queries = dest.list_queries("DestProject")
    assert len(dest_queries) == 1
    assert dest_queries[0].name == "My Active Bugs"
    assert dest_queries[0].folder_path == "Shared Queries/Team A"
    assert dest_queries[0].wiql == (
        "SELECT [System.Id] FROM WorkItems WHERE "
        "[System.AreaPath] = 'Team A (dest)' AND "
        "[System.IterationPath] UNDER 'Sprint 1 (dest)'"
    )

    destination_id = state.get_destination_id("queries", source_id="q-1")
    assert destination_id == dest_queries[0].id
    assert state.is_complete("queries", source_id="q-1")
    assert "My Active Bugs" in section.items


def test_migrate_queries_rerun_makes_no_additional_mutating_calls(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_queries(
        "SourceProject",
        [
            Query(
                id="q-1",
                name="My Active Bugs",
                folder_path="Shared Queries",
                wiql="SELECT [System.Id] FROM WorkItems",
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))

    migrate_queries(source, dest, "SourceProject", "DestProject", state)
    calls_after_first_run = len(dest.mutation_log)

    section = migrate_queries(source, dest, "SourceProject", "DestProject", state)

    assert len(dest.mutation_log) == calls_after_first_run
    assert section.items == ["My Active Bugs"]


def test_migrate_queries_recreates_query_deleted_from_destination(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_queries(
        "SourceProject",
        [
            Query(
                id="q-1",
                name="My Active Bugs",
                folder_path="Shared Queries",
                wiql="SELECT [System.Id] FROM WorkItems",
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))

    migrate_queries(source, dest, "SourceProject", "DestProject", state)
    dest._queries["DestProject"] = []

    section = migrate_queries(source, dest, "SourceProject", "DestProject", state)

    dest_queries = dest.list_queries("DestProject")
    assert len(dest_queries) == 1
    assert section.items == ["My Active Bugs"]


def test_migrate_queries_dry_run_reports_without_mutating(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=True)
    source.seed_queries(
        "SourceProject",
        [
            Query(
                id="q-1",
                name="My Active Bugs",
                folder_path="Shared Queries",
                wiql="SELECT [System.Id] FROM WorkItems",
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))

    section = migrate_queries(source, dest, "SourceProject", "DestProject", state)

    assert section.items == ["My Active Bugs"]
    assert dest.list_queries("DestProject") == []
    assert state.is_complete("queries", source_id="q-1") is False
