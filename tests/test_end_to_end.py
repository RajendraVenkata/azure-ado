from ado_migrate.cli import parse_args, run
from ado_migrate.client import (
    ArtifactFeed,
    Attachment,
    Dashboard,
    Extension,
    InMemoryFakeAdoClient,
    IterationPath,
    Link,
    Query,
    Pipeline,
    ReleasePipeline,
    Repo,
    SecurityGroup,
    ServiceConnection,
    TestPlan,
    TestSuite,
    WorkItem,
)
from ado_migrate.git_transport import InMemoryFakeGitTransport
from ado_migrate.state import StateStore


def _write_config(tmp_path, monkeypatch):
    monkeypatch.setenv("SOURCE_PAT", "s")
    monkeypatch.setenv("DEST_PAT", "d")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
        source:
          organization_url: https://dev.azure.com/source-org
          project: MyProject
          pat_env: SOURCE_PAT
        destination:
          organization_url: https://dev.azure.com/dest-org
          project: MyProject
          pat_env: DEST_PAT
        """
    )

    identity_map_path = tmp_path / "identity-map.yaml"
    identity_map_path.write_text(
        """
        mappings:
          source.user@x.com: dest.user@y.com
        """
    )

    return config_path, identity_map_path


def _seed_source(source):
    source.seed_area_paths("MyProject", ["Team A"])
    source.seed_iteration_paths(
        "MyProject",
        [IterationPath(path="Sprint 1", start_date="2026-01-01", end_date="2026-01-14")],
    )
    source.seed_repos(
        "MyProject",
        [Repo(id="repo-1", name="my-repo", clone_url="https://source/my-repo.git")],
    )
    source.seed_wikis(
        "MyProject",
        [Repo(id="wiki-1", name="MyProject.wiki", clone_url="https://source/MyProject.wiki")],
    )
    source.seed_service_connections(
        "MyProject",
        [
            ServiceConnection(
                id="sc-1",
                name="MyGitHubConn",
                connection_type="GitHub",
                config={"url": "https://github.com/example"},
            )
        ],
    )
    source.seed_work_items(
        "MyProject",
        [
            WorkItem(
                id="1",
                work_item_type="Bug",
                revisions=[
                    {
                        "Title": "Crash on save",
                        "State": "New",
                        "AreaPath": "Team A",
                        "IterationPath": "Sprint 1",
                        "AssignedTo": "source.user@x.com",
                    }
                ],
                attachments=[Attachment(name="crash.log", content=b"stack trace")],
                links=[
                    Link(link_type="work_item", target="2"),
                    Link(link_type="pull_request", target="repo-1:42"),
                ],
            ),
            WorkItem(
                id="2",
                work_item_type="Task",
                revisions=[{"Title": "Fix the crash"}],
            ),
        ],
    )
    source.seed_queries(
        "MyProject",
        [
            Query(
                id="q-1",
                name="My Active Bugs",
                folder_path="Shared Queries",
                wiql="SELECT [System.Id] FROM WorkItems WHERE [System.AreaPath] = 'Team A'",
            )
        ],
    )
    source.seed_pipelines(
        "MyProject",
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
    source.seed_test_plans(
        "MyProject",
        [
            TestPlan(
                id="tp-1",
                name="Release 1 Test Plan",
                suites=[
                    TestSuite(
                        id="ts-1",
                        name="Smoke Tests",
                        test_case_ids=["1"],
                        configuration_names=["Windows 10 + Chrome"],
                    )
                ],
            )
        ],
    )
    source.seed_security_groups(
        "MyProject",
        [
            SecurityGroup(
                id="sg-1",
                name="Release Managers",
                member_identities=["source.user@x.com"],
            )
        ],
    )
    source.seed_release_pipelines(
        "MyProject", [ReleasePipeline(id="rp-1", name="Deploy to Prod")]
    )
    source.seed_dashboards(
        "MyProject",
        [Dashboard(id="db-1", name="Team Overview", widgets=["Burndown"])],
    )
    source.seed_artifact_feeds(
        "MyProject", [ArtifactFeed(id="feed-1", name="internal-npm")]
    )
    source.seed_used_extensions(
        "MyProject", [Extension(id="ext-1", name="SonarQube")]
    )


def test_dry_run_then_real_run_then_rerun_end_to_end(tmp_path, monkeypatch):
    config_path, identity_map_path = _write_config(tmp_path, monkeypatch)

    source = InMemoryFakeAdoClient(dry_run=False)
    _seed_source(source)
    dest_dry = InMemoryFakeAdoClient(dry_run=True)
    git_dry = InMemoryFakeGitTransport(dry_run=True)

    dry_run_args = parse_args(
        ["--config", str(config_path), "--identity-map", str(identity_map_path), "--dry-run"]
    )
    dry_exit = run(dry_run_args, source, dest_dry, git_dry)

    assert dry_exit == 0
    report_html = (tmp_path / "report.html").read_text()
    for expected in [
        "Team A",
        "Sprint 1",
        "my-repo",
        "MyProject.wiki",
        "MyGitHubConn",
        "My Active Bugs",
        "CI",
        "Release 1 Test Plan",
        "Release Managers (1 members)",
        "Deploy to Prod",
        "Team Overview (1 widgets)",
        "internal-npm",
        "SonarQube",
    ]:
        assert expected in report_html, f"{expected!r} missing from dry-run report"

    assert not any(record.executed for record in dest_dry.mutation_log)
    assert not any(record.executed for record in git_dry.mutation_log)
    dry_state = StateStore(str(tmp_path / "state.json"))
    dry_state.load()
    assert dry_state.list_destination_ids("area_paths") == {}

    # --- real run ---
    dest = InMemoryFakeAdoClient(dry_run=False)
    git_transport = InMemoryFakeGitTransport(dry_run=False)
    real_args = parse_args(
        ["--config", str(config_path), "--identity-map", str(identity_map_path)]
    )
    real_exit = run(real_args, source, dest, git_transport)

    assert real_exit == 0
    state = StateStore(str(tmp_path / "state.json"))
    state.load()

    for artifact_type, source_id in [
        ("area_paths", "Team A"),
        ("iteration_paths", "Sprint 1"),
        ("repos", "repo-1"),
        ("wikis", "wiki-1"),
        ("service_connections", "sc-1"),
        ("work_items", "1"),
        ("work_items", "2"),
        ("queries", "q-1"),
        ("pipelines", "pl-1"),
        ("test_plans", "tp-1"),
        ("security_groups", "sg-1"),
    ]:
        destination_id = state.get_destination_id(artifact_type, source_id=source_id)
        assert destination_id, f"{artifact_type}/{source_id} was not migrated"

    dest_work_item_1 = dest.get_work_item(
        "MyProject", state.get_destination_id("work_items", source_id="1")
    )
    dest_work_item_2_id = state.get_destination_id("work_items", source_id="2")
    dest_repo_id = state.get_destination_id("repos", source_id="repo-1")
    assert dest_work_item_1.links == [
        Link(link_type="work_item", target=dest_work_item_2_id),
        Link(link_type="pull_request", target=f"{dest_repo_id}:42"),
    ]
    assert dest_work_item_1.attachments == [
        Attachment(name="crash.log", content=b"stack trace")
    ]
    assert dest_work_item_1.revisions[0]["AssignedTo"] == "dest.user@y.com"

    real_report_html = (tmp_path / "report.html").read_text()
    assert "Deploy to Prod" in real_report_html

    # --- rerun: idempotent, no duplicates ---
    dest_mutations_before = len(dest.mutation_log)
    git_mutations_before = len(git_transport.mutation_log)
    state_bytes_before = (tmp_path / "state.json").read_bytes()

    rerun_exit = run(real_args, source, dest, git_transport)

    assert rerun_exit == 0
    assert len(dest.mutation_log) == dest_mutations_before
    assert len(git_transport.mutation_log) == git_mutations_before
    assert (tmp_path / "state.json").read_bytes() == state_bytes_before
