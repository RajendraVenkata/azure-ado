from ado_migrate.client import InMemoryFakeAdoClient
from ado_migrate.identity import IdentityMap
from ado_migrate.users import migrate_users


def test_migrate_users_reports_resolved_identity(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    source.seed_project_users("SourceProject", ["alice@x.com"])
    identity_map = IdentityMap({"alice@x.com": "alice@y.com"})

    section = migrate_users(source, "SourceProject", identity_map)

    assert section.items == ["alice@x.com -> alice@y.com"]


def test_migrate_users_reports_unmapped_identity(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    source.seed_project_users("SourceProject", ["bob@x.com"])
    identity_map = IdentityMap({})

    section = migrate_users(source, "SourceProject", identity_map)

    assert section.items == ["bob@x.com -> UNMAPPED (no destination identity configured)"]


def test_migrate_users_reports_each_distinct_identity_once_sorted(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    source.seed_project_users("SourceProject", ["bob@x.com", "alice@x.com", "alice@x.com"])
    identity_map = IdentityMap({"alice@x.com": "alice@y.com", "bob@x.com": "bob@y.com"})

    section = migrate_users(source, "SourceProject", identity_map)

    assert section.items == [
        "alice@x.com -> alice@y.com",
        "bob@x.com -> bob@y.com",
    ]
