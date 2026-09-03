from ado_migrate.client import InMemoryFakeAdoClient, Repo
from ado_migrate.git_transport import InMemoryFakeGitTransport
from ado_migrate.state import StateStore
from ado_migrate.wikis import migrate_wikis


def test_migrate_wikis_creates_and_pushes_single_wiki(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    git_transport = InMemoryFakeGitTransport(dry_run=False)
    source.seed_wikis(
        "SourceProject",
        [Repo(id="wiki-1", name="SourceProject.wiki", clone_url="https://source/SourceProject.wiki")],
    )
    state = StateStore(str(tmp_path / "state.json"))

    section = migrate_wikis(
        source, dest, git_transport, "SourceProject", "DestProject", state
    )

    dest_wikis = dest.list_wikis("DestProject")
    assert len(dest_wikis) == 1
    assert dest_wikis[0].name == "SourceProject.wiki"

    destination_id = state.get_destination_id("wikis", source_id="wiki-1")
    assert destination_id == dest_wikis[0].id
    assert git_transport.pushed == [
        ("https://source/SourceProject.wiki", dest_wikis[0].clone_url)
    ]
    assert state.is_complete("wikis", source_id="wiki-1")
    assert "SourceProject.wiki" in section.items


def test_migrate_wikis_rerun_makes_no_additional_mutating_calls(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    git_transport = InMemoryFakeGitTransport(dry_run=False)
    source.seed_wikis(
        "SourceProject",
        [Repo(id="wiki-1", name="SourceProject.wiki", clone_url="https://source/SourceProject.wiki")],
    )
    state = StateStore(str(tmp_path / "state.json"))

    migrate_wikis(source, dest, git_transport, "SourceProject", "DestProject", state)
    dest_calls_after_first_run = len(dest.mutation_log)
    push_calls_after_first_run = len(git_transport.mutation_log)

    section = migrate_wikis(
        source, dest, git_transport, "SourceProject", "DestProject", state
    )

    assert len(dest.mutation_log) == dest_calls_after_first_run
    assert len(git_transport.mutation_log) == push_calls_after_first_run
    assert section.items == ["SourceProject.wiki"]


def test_migrate_wikis_dry_run_reports_without_mutating(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=True)
    git_transport = InMemoryFakeGitTransport(dry_run=True)
    source.seed_wikis(
        "SourceProject",
        [Repo(id="wiki-1", name="SourceProject.wiki", clone_url="https://source/SourceProject.wiki")],
    )
    state = StateStore(str(tmp_path / "state.json"))

    section = migrate_wikis(
        source, dest, git_transport, "SourceProject", "DestProject", state
    )

    assert section.items == ["SourceProject.wiki"]
    assert dest.list_wikis("DestProject") == []
    assert git_transport.pushed == []
    assert state.is_complete("wikis", source_id="wiki-1") is False
