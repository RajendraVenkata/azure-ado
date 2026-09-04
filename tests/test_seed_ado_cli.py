from ado_migrate.seed_ado import parse_args, render_seeded_config


def test_parse_args_reads_required_flags():
    args = parse_args(
        ["--org", "https://dev.azure.com/myorg", "--pat-env", "ADO_PAT", "--project-prefix", "migration-test"]
    )

    assert args.org == "https://dev.azure.com/myorg"
    assert args.pat_env == "ADO_PAT"
    assert args.project_prefix == "migration-test"
    assert args.work_item_count == 10


def test_render_seeded_config_fills_source_and_placeholders_destination():
    import yaml

    content = render_seeded_config(
        organization_url="https://dev.azure.com/myorg",
        project_name="migration-test-20260101",
        pat_env="ADO_PAT",
    )
    parsed = yaml.safe_load(content)

    assert parsed["source"] == {
        "organization_url": "https://dev.azure.com/myorg",
        "project": "migration-test-20260101",
        "pat_env": "ADO_PAT",
    }
    assert parsed["destination"]["organization_url"] == "CHANGE_ME"
    assert parsed["destination"]["project"] == "CHANGE_ME"
    assert parsed["destination"]["pat_env"] == "CHANGE_ME"
