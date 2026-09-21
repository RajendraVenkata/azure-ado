from ado_migrate.client import InMemoryFakeAdoClient, Repo
from ado_migrate.git_transport import InMemoryFakeGitTransport
from ado_migrate.repos import migrate_repos
from ado_migrate.state import StateStore


def test_migrate_repos_creates_and_pushes_single_repo(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    git_transport = InMemoryFakeGitTransport(dry_run=False)
    source.seed_repos(
        "SourceProject",
        [Repo(id="repo-1", name="my-repo", clone_url="https://source/my-repo.git")],
    )
    state = StateStore(str(tmp_path / "state.json"))

    section = migrate_repos(
        source, dest, git_transport, "SourceProject", "DestProject", state
    )

    dest_repos = dest.list_repos("DestProject")
    assert len(dest_repos) == 1
    assert dest_repos[0].name == "my-repo"

    destination_id = state.get_destination_id("repos", source_id="repo-1")
    assert destination_id == dest_repos[0].id
    assert git_transport.pushed == [
        ("https://source/my-repo.git", dest_repos[0].clone_url)
    ]
    assert state.is_complete("repos", source_id="repo-1")
    assert "my-repo" in section.items


def test_migrate_repos_rerun_makes_no_additional_mutating_calls(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    git_transport = InMemoryFakeGitTransport(dry_run=False)
    source.seed_repos(
        "SourceProject",
        [Repo(id="repo-1", name="my-repo", clone_url="https://source/my-repo.git")],
    )
    state = StateStore(str(tmp_path / "state.json"))

    migrate_repos(source, dest, git_transport, "SourceProject", "DestProject", state)
    dest_calls_after_first_run = len(dest.mutation_log)
    push_calls_after_first_run = len(git_transport.mutation_log)

    section = migrate_repos(
        source, dest, git_transport, "SourceProject", "DestProject", state
    )

    assert len(dest.mutation_log) == dest_calls_after_first_run
    assert len(git_transport.mutation_log) == push_calls_after_first_run
    assert section.items == ["my-repo"]


def test_migrate_repos_recreates_repo_deleted_from_destination(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    git_transport = InMemoryFakeGitTransport(dry_run=False)
    source.seed_repos(
        "SourceProject",
        [Repo(id="repo-1", name="my-repo", clone_url="https://source/my-repo.git")],
    )
    state = StateStore(str(tmp_path / "state.json"))

    migrate_repos(source, dest, git_transport, "SourceProject", "DestProject", state)
    first_destination_id = state.get_destination_id("repos", source_id="repo-1")

    # Simulate someone deleting the migrated repo directly in the destination,
    # out-of-band from this tool — state.json still says it's complete.
    dest._repos["DestProject"] = []

    section = migrate_repos(
        source, dest, git_transport, "SourceProject", "DestProject", state
    )

    dest_repos = dest.list_repos("DestProject")
    assert len(dest_repos) == 1
    assert dest_repos[0].name == "my-repo"
    new_destination_id = state.get_destination_id("repos", source_id="repo-1")
    assert new_destination_id == dest_repos[0].id
    assert new_destination_id != first_destination_id
    assert section.items == ["my-repo"]


def test_migrate_repos_skips_push_for_untracked_name_collision(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    git_transport = InMemoryFakeGitTransport(dry_run=False)
    source.seed_repos(
        "SourceProject",
        [
            Repo(id="repo-1", name="RG_DnA", clone_url="https://source/RG_DnA.git"),
            Repo(id="repo-2", name="other-repo", clone_url="https://source/other-repo.git"),
        ],
    )
    # RG_DnA already exists in the destination, but not via this tool (no
    # state record for it) — simulates a repo created before the migration
    # ran, which previously made create_repo() fail with a duplicate-name
    # error and aborted the whole step before other-repo was processed.
    dest.seed_repos(
        "DestProject",
        [Repo(id="existing-repo", name="RG_DnA", clone_url="https://dest/RG_DnA.git")],
    )
    state = StateStore(str(tmp_path / "state.json"))

    section = migrate_repos(
        source, dest, git_transport, "SourceProject", "DestProject", state
    )

    dest_repos = {r.name: r for r in dest.list_repos("DestProject")}
    assert set(dest_repos) == {"RG_DnA", "other-repo"}
    assert git_transport.pushed == [
        ("https://source/other-repo.git", dest_repos["other-repo"].clone_url)
    ]
    assert state.get_destination_id("repos", source_id="repo-1") == "existing-repo"
    assert state.get_destination_id("repos", source_id="repo-2") == dest_repos["other-repo"].id
    assert section.items == [
        "RG_DnA (already exists in destination, not pushed)",
        "other-repo",
    ]


def test_migrate_repos_dry_run_reports_without_mutating(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=True)
    git_transport = InMemoryFakeGitTransport(dry_run=True)
    source.seed_repos(
        "SourceProject",
        [Repo(id="repo-1", name="my-repo", clone_url="https://source/my-repo.git")],
    )
    state = StateStore(str(tmp_path / "state.json"))

    section = migrate_repos(
        source, dest, git_transport, "SourceProject", "DestProject", state
    )

    assert section.items == ["my-repo"]
    assert dest.list_repos("DestProject") == []
    assert git_transport.pushed == []
    assert state.is_complete("repos", source_id="repo-1") is False
