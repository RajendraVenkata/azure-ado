from ado_migrate.client import InMemoryFakeAdoClient, Repo, WorkItem
from ado_migrate.mutation import TransientError
from ado_migrate.git_transport import InMemoryFakeGitTransport
from ado_migrate.identity import IdentityMap
from ado_migrate.orchestrator import run_migration
from ado_migrate.state import StateStore

EXPECTED_SECTION_TITLES = {
    "Users",
    "Area Paths",
    "Iteration Paths",
    "Teams",
    "Repositories",
    "Wikis",
    "Service Connections",
    "Work Items",
    "Queries",
    "Pipelines",
    "Test Plans",
    "Security Groups",
    "External References Retained",
    "Classic Release Pipelines",
    "Dashboards",
    "Artifact Feeds",
    "Marketplace Extensions",
}


def test_run_migration_executes_every_type_with_no_seeded_data(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    git_transport = InMemoryFakeGitTransport(dry_run=False)
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({})

    report = run_migration(
        source, dest, git_transport, "SourceProject", "DestProject", state, identity_map
    )

    section_titles = {s.title for s in report.sections}
    assert section_titles == EXPECTED_SECTION_TITLES


def test_run_migration_only_restricts_to_specified_types(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    git_transport = InMemoryFakeGitTransport(dry_run=False)
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({})

    report = run_migration(
        source,
        dest,
        git_transport,
        "SourceProject",
        "DestProject",
        state,
        identity_map,
        only={"repos"},
    )

    section_titles = {s.title for s in report.sections}
    assert section_titles == {"Repositories"}


def test_run_migration_continues_past_persistent_type_failure(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    git_transport = InMemoryFakeGitTransport(dry_run=False)
    source.seed_repos(
        "SourceProject",
        [Repo(id="repo-1", name="my-repo", clone_url="https://source/my-repo.git")],
    )
    source.seed_work_items(
        "SourceProject",
        [WorkItem(id="1", work_item_type="Bug", revisions=[{"Title": "Crash"}])],
    )
    dest.queue_failure(RuntimeError("destination org unreachable"))
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({})

    report = run_migration(
        source, dest, git_transport, "SourceProject", "DestProject", state, identity_map
    )

    assert state.get_failures("repos") == ["destination org unreachable"]
    failures_section = next(s for s in report.sections if s.title == "Failures")
    assert failures_section.items == ["repos: destination org unreachable"]

    assert state.is_complete("work_items", source_id="1")
    work_items_section = next(s for s in report.sections if s.title == "Work Items")
    assert work_items_section.items == ["1"]


def test_run_migration_reports_users_from_project_permissions(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    git_transport = InMemoryFakeGitTransport(dry_run=False)
    source.seed_project_users("SourceProject", ["alice@x.com", "bob@x.com"])
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({"alice@x.com": "alice@y.com"})

    report = run_migration(
        source,
        dest,
        git_transport,
        "SourceProject",
        "DestProject",
        state,
        identity_map,
        only={"users"},
    )

    users_section = next(s for s in report.sections if s.title == "Users")
    assert users_section.items == [
        "alice@x.com -> alice@y.com",
        "bob@x.com -> UNMAPPED (no destination identity configured)",
    ]
    assert dest.list_project_members("DestProject") == ["alice@y.com"]


def test_run_migration_reports_users_even_when_not_referenced_by_work_items(
    tmp_path,
):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    git_transport = InMemoryFakeGitTransport(dry_run=False)
    source.seed_project_users("SourceProject", ["alice@x.com"])
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({"alice@x.com": "alice@y.com"})

    report = run_migration(
        source, dest, git_transport, "SourceProject", "DestProject", state, identity_map
    )

    users_section = next(s for s in report.sections if s.title == "Users")
    assert users_section.items == ["alice@x.com -> alice@y.com"]
    assert dest.list_project_members("DestProject") == ["alice@y.com"]


def test_run_migration_transient_failure_does_not_surface_as_a_failure(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    git_transport = InMemoryFakeGitTransport(dry_run=False)
    source.seed_repos(
        "SourceProject",
        [Repo(id="repo-1", name="my-repo", clone_url="https://source/my-repo.git")],
    )
    dest.queue_failure(TransientError("rate limited"))
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({})

    report = run_migration(
        source, dest, git_transport, "SourceProject", "DestProject", state, identity_map
    )

    assert state.get_failures("repos") == []
    assert not any(s.title == "Failures" for s in report.sections)
    assert state.is_complete("repos", source_id="repo-1")
