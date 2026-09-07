from ado_migrate.identity import UNMAPPED_PLACEHOLDER, load_identity_map


def test_resolve_returns_mapped_destination_identity(tmp_path):
    mapping_path = tmp_path / "identity-map.yaml"
    mapping_path.write_text(
        """
        mappings:
          source.user@x.com: dest.user@y.com
          another@x.com: another@y.com
        """
    )

    identity_map = load_identity_map(str(mapping_path))

    assert identity_map.resolve("source.user@x.com") == "dest.user@y.com"
    assert identity_map.resolve("another@x.com") == "another@y.com"


def test_resolve_falls_back_to_placeholder_for_unmapped_identity(tmp_path):
    mapping_path = tmp_path / "identity-map.yaml"
    mapping_path.write_text(
        """
        mappings:
          source.user@x.com: dest.user@y.com
        """
    )

    identity_map = load_identity_map(str(mapping_path))

    assert identity_map.resolve("nobody@x.com") == UNMAPPED_PLACEHOLDER
    assert "nobody@x.com" in identity_map.unmapped_identities


def test_report_items_lists_each_distinct_identity_once_sorted(tmp_path):
    mapping_path = tmp_path / "identity-map.yaml"
    mapping_path.write_text(
        """
        mappings:
          bob@x.com: bob@y.com
          alice@x.com: alice@y.com
        """
    )
    identity_map = load_identity_map(str(mapping_path))

    identity_map.resolve("bob@x.com")
    identity_map.resolve("alice@x.com")
    identity_map.resolve("alice@x.com")  # referenced twice, e.g. two revisions
    identity_map.resolve("nobody@x.com")

    assert identity_map.report_items() == [
        "alice@x.com -> alice@y.com",
        "bob@x.com -> bob@y.com",
        "nobody@x.com -> UNMAPPED (no destination identity configured)",
    ]
