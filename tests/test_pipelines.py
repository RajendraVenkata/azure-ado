from ado_migrate.client import InMemoryFakeAdoClient, Pipeline
from ado_migrate.pipelines import migrate_pipelines
from ado_migrate.state import StateStore


def test_migrate_pipelines_remaps_repo_and_service_connection_references(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_pipelines(
        "SourceProject",
        [
            Pipeline(
                id="pl-1",
                name="CI",
                yaml_path="/azure-pipelines.yml",
                repo_id="repo-1",
                service_connection_ids=["sc-1"],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))
    state.mark_complete("repos", source_id="repo-1", destination_id="repo-9")
    state.mark_complete("service_connections", source_id="sc-1", destination_id="sc-9")

    section = migrate_pipelines(
        source, dest, "SourceProject", "DestProject", state
    )

    dest_pipelines = dest.list_pipelines("DestProject")
    assert len(dest_pipelines) == 1
    assert dest_pipelines[0].name == "CI"
    assert dest_pipelines[0].repo_id == "repo-9"
    assert dest_pipelines[0].service_connection_ids == ["sc-9"]

    destination_id = state.get_destination_id("pipelines", source_id="pl-1")
    assert destination_id == dest_pipelines[0].id
    assert state.is_complete("pipelines", source_id="pl-1")
    assert "CI" in section.items


def test_migrate_pipelines_keeps_original_reference_when_no_mapping_exists(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_pipelines(
        "SourceProject",
        [
            Pipeline(
                id="pl-1",
                name="CI",
                yaml_path="/azure-pipelines.yml",
                repo_id="repo-unmigrated",
                service_connection_ids=["sc-unmigrated"],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))

    migrate_pipelines(source, dest, "SourceProject", "DestProject", state)

    dest_pipelines = dest.list_pipelines("DestProject")
    assert dest_pipelines[0].repo_id == "repo-unmigrated"
    assert dest_pipelines[0].service_connection_ids == ["sc-unmigrated"]


def test_migrate_pipelines_rerun_makes_no_additional_mutating_calls(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_pipelines(
        "SourceProject",
        [
            Pipeline(
                id="pl-1",
                name="CI",
                yaml_path="/azure-pipelines.yml",
                repo_id="repo-1",
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))

    migrate_pipelines(source, dest, "SourceProject", "DestProject", state)
    calls_after_first_run = len(dest.mutation_log)

    section = migrate_pipelines(source, dest, "SourceProject", "DestProject", state)

    assert len(dest.mutation_log) == calls_after_first_run
    assert section.items == ["CI"]


def test_migrate_pipelines_recreates_pipeline_deleted_from_destination(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_pipelines(
        "SourceProject",
        [
            Pipeline(
                id="pl-1",
                name="CI",
                yaml_path="/azure-pipelines.yml",
                repo_id="repo-1",
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))

    migrate_pipelines(source, dest, "SourceProject", "DestProject", state)
    dest._pipelines["DestProject"] = []

    section = migrate_pipelines(source, dest, "SourceProject", "DestProject", state)

    dest_pipelines = dest.list_pipelines("DestProject")
    assert len(dest_pipelines) == 1
    assert section.items == ["CI"]


def test_migrate_pipelines_dry_run_reports_without_mutating(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=True)
    source.seed_pipelines(
        "SourceProject",
        [
            Pipeline(
                id="pl-1",
                name="CI",
                yaml_path="/azure-pipelines.yml",
                repo_id="repo-1",
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))

    section = migrate_pipelines(source, dest, "SourceProject", "DestProject", state)

    assert section.items == ["CI"]
    assert dest.list_pipelines("DestProject") == []
    assert state.is_complete("pipelines", source_id="pl-1") is False
