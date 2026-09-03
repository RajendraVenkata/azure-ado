from ado_migrate.client import InMemoryFakeAdoClient, SecurityGroup
from ado_migrate.identity import IdentityMap
from ado_migrate.security_groups import migrate_security_groups
from ado_migrate.state import StateStore


def test_migrate_security_groups_creates_group_with_resolved_members(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_security_groups(
        "SourceProject",
        [
            SecurityGroup(
                id="sg-1",
                name="Release Managers",
                member_identities=["source.user@x.com"],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({"source.user@x.com": "dest.user@y.com"})

    section = migrate_security_groups(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    dest_groups = dest.list_security_groups("DestProject")
    assert len(dest_groups) == 1
    assert dest_groups[0].name == "Release Managers"
    assert dest_groups[0].member_identities == ["dest.user@y.com"]

    destination_id = state.get_destination_id("security_groups", source_id="sg-1")
    assert destination_id == dest_groups[0].id
    assert state.is_complete("security_groups", source_id="sg-1")
    assert section.items == ["Release Managers (1 members)"]


def test_migrate_security_groups_skips_unmapped_member_without_fabricating_identity(
    tmp_path,
):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_security_groups(
        "SourceProject",
        [
            SecurityGroup(
                id="sg-1",
                name="Release Managers",
                member_identities=["source.user@x.com", "nobody@x.com"],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({"source.user@x.com": "dest.user@y.com"})

    section = migrate_security_groups(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    dest_groups = dest.list_security_groups("DestProject")
    assert dest_groups[0].member_identities == ["dest.user@y.com"]
    assert section.items == [
        "Release Managers: nobody@x.com has no destination mapping, skipped",
        "Release Managers (1 members)",
    ]


def test_migrate_security_groups_rerun_makes_no_additional_mutating_calls(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_security_groups(
        "SourceProject",
        [SecurityGroup(id="sg-1", name="Release Managers", member_identities=[])],
    )
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({})

    migrate_security_groups(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )
    calls_after_first_run = len(dest.mutation_log)

    section = migrate_security_groups(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    assert len(dest.mutation_log) == calls_after_first_run
    assert section.items == ["Release Managers (0 members)"]


def test_migrate_security_groups_dry_run_reports_without_mutating(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=True)
    source.seed_security_groups(
        "SourceProject",
        [
            SecurityGroup(
                id="sg-1",
                name="Release Managers",
                member_identities=["source.user@x.com"],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({"source.user@x.com": "dest.user@y.com"})

    section = migrate_security_groups(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    assert section.items == ["Release Managers (1 members)"]
    assert dest.list_security_groups("DestProject") == []
    assert state.is_complete("security_groups", source_id="sg-1") is False
