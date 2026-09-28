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


def test_migrate_security_groups_recreates_group_deleted_from_destination(tmp_path):
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
    dest._security_groups["DestProject"] = []

    section = migrate_security_groups(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    assert len(dest.list_security_groups("DestProject")) == 1
    assert section.items == ["Release Managers (0 members)"]


def test_migrate_security_groups_reports_members_the_destination_could_not_resolve(
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
                member_identities=["source.user@x.com", "source.other@x.com"],
            )
        ],
    )
    # dest.user@y.com resolves through the identity map but doesn't exist in
    # the destination org's directory yet, so the destination API silently
    # drops it when creating the group.
    dest.unresolvable_identities = {"dest.user@y.com"}
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap(
        {
            "source.user@x.com": "dest.user@y.com",
            "source.other@x.com": "dest.other@y.com",
        }
    )

    section = migrate_security_groups(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    dest_groups = dest.list_security_groups("DestProject")
    assert dest_groups[0].member_identities == ["dest.other@y.com"]
    assert section.items == [
        "Release Managers: dest.user@y.com could not be added in the "
        "destination organization (identity not found), skipped",
        "Release Managers (1 members)",
    ]


def test_migrate_security_groups_mirrors_default_group_membership(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_security_groups(
        "SourceProject",
        [
            SecurityGroup(
                id="g-readers",
                name="Readers",
                member_identities=["source.reader@x.com"],
            )
        ],
    )
    # Every project already has its built-in groups; the destination's
    # Readers group pre-exists with a different id/membership than the
    # source's, the way a real destination project would.
    dest.seed_security_groups(
        "DestProject",
        [SecurityGroup(id="dest-readers-group", name="Readers", member_identities=[])],
    )
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({"source.reader@x.com": "dest.reader@y.com"})

    section = migrate_security_groups(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    dest_groups = {g.name: g for g in dest.list_security_groups("DestProject")}
    assert dest_groups["Readers"].id == "dest-readers-group"
    assert dest_groups["Readers"].member_identities == ["dest.reader@y.com"]
    assert section.items == ["Readers (1 members)"]


def test_migrate_security_groups_does_not_dump_everyone_into_contributors(tmp_path):
    """A user who was only ever a Reader on the source must not become a
    Contributor on the destination just because they were migrated."""
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_security_groups(
        "SourceProject",
        [
            SecurityGroup(id="g-readers", name="Readers", member_identities=["reader@x.com"]),
            SecurityGroup(
                id="g-contrib", name="Contributors", member_identities=["writer@x.com"]
            ),
        ],
    )
    dest.seed_security_groups(
        "DestProject",
        [
            SecurityGroup(id="dest-readers", name="Readers", member_identities=[]),
            SecurityGroup(id="dest-contrib", name="Contributors", member_identities=[]),
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({"reader@x.com": "reader@y.com", "writer@x.com": "writer@y.com"})

    migrate_security_groups(source, dest, "SourceProject", "DestProject", state, identity_map)

    dest_groups = {g.name: g for g in dest.list_security_groups("DestProject")}
    assert dest_groups["Readers"].member_identities == ["reader@y.com"]
    assert dest_groups["Contributors"].member_identities == ["writer@y.com"]


def test_migrate_security_groups_reports_default_group_missing_in_destination(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_security_groups(
        "SourceProject",
        [
            SecurityGroup(
                id="g-readers", name="Readers", member_identities=["reader@x.com"]
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({"reader@x.com": "reader@y.com"})

    section = migrate_security_groups(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    assert section.items == [
        "Readers: not found in the destination project, skipped",
        "Readers (0 members)",
    ]


def test_migrate_security_groups_default_group_rerun_makes_no_additional_mutating_calls(
    tmp_path,
):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_security_groups(
        "SourceProject",
        [SecurityGroup(id="g-readers", name="Readers", member_identities=["reader@x.com"])],
    )
    dest.seed_security_groups(
        "DestProject",
        [SecurityGroup(id="dest-readers", name="Readers", member_identities=[])],
    )
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({"reader@x.com": "reader@y.com"})

    migrate_security_groups(source, dest, "SourceProject", "DestProject", state, identity_map)
    calls_after_first_run = len(dest.mutation_log)

    section = migrate_security_groups(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    assert len(dest.mutation_log) == calls_after_first_run
    assert section.items == ["Readers (1 members)"]


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
