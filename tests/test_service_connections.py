from ado_migrate.client import InMemoryFakeAdoClient, ServiceConnection
from ado_migrate.service_connections import migrate_service_connections
from ado_migrate.state import StateStore


def test_migrate_service_connections_creates_connection_without_secret(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_service_connections(
        "SourceProject",
        [
            ServiceConnection(
                id="sc-1",
                name="MyGitHubConn",
                connection_type="GitHub",
                config={"url": "https://github.com/example"},
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))

    section = migrate_service_connections(
        source, dest, "SourceProject", "DestProject", state
    )

    dest_connections = dest.list_service_connections("DestProject")
    assert len(dest_connections) == 1
    assert dest_connections[0].name == "MyGitHubConn"
    assert dest_connections[0].connection_type == "GitHub"
    assert dest_connections[0].config == {"url": "https://github.com/example"}

    destination_id = state.get_destination_id("service_connections", source_id="sc-1")
    assert destination_id == dest_connections[0].id
    assert state.is_complete("service_connections", source_id="sc-1")
    assert section.items == ["MyGitHubConn (GitHub)"]


def test_migrate_service_connections_dry_run_reports_without_mutating(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=True)
    source.seed_service_connections(
        "SourceProject",
        [
            ServiceConnection(
                id="sc-1", name="MyGitHubConn", connection_type="GitHub", config={}
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))

    section = migrate_service_connections(
        source, dest, "SourceProject", "DestProject", state
    )

    assert section.items == ["MyGitHubConn (GitHub)"]
    assert dest.list_service_connections("DestProject") == []
    assert state.is_complete("service_connections", source_id="sc-1") is False


def test_migrate_service_connections_flags_secret_gap_without_fabricating_a_value(
    tmp_path,
):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_service_connections(
        "SourceProject",
        [
            ServiceConnection(
                id="sc-1",
                name="MyAzureConn",
                connection_type="AzureRM",
                config={"subscription_id": "sub-123"},
                has_secret=True,
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))

    section = migrate_service_connections(
        source, dest, "SourceProject", "DestProject", state
    )

    dest_connections = dest.list_service_connections("DestProject")
    assert dest_connections[0].config == {"subscription_id": "sub-123"}
    assert section.items == [
        "MyAzureConn (AzureRM) - secret must be re-entered manually"
    ]


def test_migrate_service_connections_rerun_makes_no_additional_mutating_calls(
    tmp_path,
):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_service_connections(
        "SourceProject",
        [
            ServiceConnection(
                id="sc-1", name="MyGitHubConn", connection_type="GitHub", config={}
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))

    migrate_service_connections(source, dest, "SourceProject", "DestProject", state)
    calls_after_first_run = len(dest.mutation_log)

    section = migrate_service_connections(
        source, dest, "SourceProject", "DestProject", state
    )

    assert len(dest.mutation_log) == calls_after_first_run
    assert section.items == ["MyGitHubConn (GitHub)"]
