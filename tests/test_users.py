from ado_migrate.client import InMemoryFakeAdoClient
from ado_migrate.identity import IdentityMap
from ado_migrate.state import StateStore
from ado_migrate.users import migrate_users


def test_migrate_users_adds_mapped_identity_as_destination_project_member(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_project_users("SourceProject", ["alice@x.com"])
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({"alice@x.com": "alice@y.com"})

    section = migrate_users(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    assert dest.list_project_members("DestProject") == ["alice@y.com"]
    assert state.is_complete("users", source_id="alice@x.com")
    assert section.items == ["alice@x.com -> alice@y.com"]


def test_migrate_users_does_not_add_unmapped_identity(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_project_users("SourceProject", ["bob@x.com"])
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({})

    section = migrate_users(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    assert dest.list_project_members("DestProject") == []
    assert section.items == ["bob@x.com -> UNMAPPED (no destination identity configured)"]


def test_migrate_users_dry_run_reports_without_mutating(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=True)
    source.seed_project_users("SourceProject", ["alice@x.com"])
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({"alice@x.com": "alice@y.com"})

    section = migrate_users(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    assert section.items == ["alice@x.com -> alice@y.com"]
    assert dest.list_project_members("DestProject") == []
    assert state.is_complete("users", source_id="alice@x.com") is False
    assert all(not record.executed for record in dest.mutation_log)


def test_migrate_users_re_adds_member_removed_from_destination(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_project_users("SourceProject", ["alice@x.com"])
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({"alice@x.com": "alice@y.com"})

    migrate_users(source, dest, "SourceProject", "DestProject", state, identity_map)
    dest._project_members["DestProject"] = []

    section = migrate_users(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    assert dest.list_project_members("DestProject") == ["alice@y.com"]
    assert section.items == ["alice@x.com -> alice@y.com"]


def test_migrate_users_rerun_makes_no_additional_mutating_calls(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_project_users("SourceProject", ["alice@x.com"])
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({"alice@x.com": "alice@y.com"})

    migrate_users(source, dest, "SourceProject", "DestProject", state, identity_map)
    calls_after_first_run = len(dest.mutation_log)

    section = migrate_users(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    assert len(dest.mutation_log) == calls_after_first_run
    assert section.items == ["alice@x.com -> alice@y.com"]
