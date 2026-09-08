import os

import pytest

from ado_migrate.config import ConfigError, load_config, state_dir_parts


def test_load_config_resolves_pat_env_vars(tmp_path, monkeypatch):
    monkeypatch.setenv("SOURCE_PAT", "source-token-123")
    monkeypatch.setenv("DEST_PAT", "dest-token-456")

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

    config = load_config(str(config_path))

    assert config.source.organization_url == "https://dev.azure.com/source-org"
    assert config.source.project == "MyProject"
    assert config.source.pat == "source-token-123"
    assert config.destination.organization_url == "https://dev.azure.com/dest-org"
    assert config.destination.project == "MyProject"
    assert config.destination.pat == "dest-token-456"


def test_load_config_raises_clear_error_for_missing_env_var(tmp_path, monkeypatch):
    monkeypatch.delenv("MISSING_PAT", raising=False)

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
        source:
          organization_url: https://dev.azure.com/source-org
          project: MyProject
          pat_env: MISSING_PAT
        destination:
          organization_url: https://dev.azure.com/dest-org
          project: MyProject
          pat_env: MISSING_PAT
        """
    )

    with pytest.raises(ConfigError, match="MISSING_PAT"):
        load_config(str(config_path))


def test_state_dir_parts_uniquely_identifies_source_and_destination_pair(
    tmp_path, monkeypatch
):
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

    config = load_config(str(config_path))

    assert state_dir_parts(config) == [
        "source-org",
        "MyProject",
        "dest-org",
        "MyProject",
    ]


def test_state_dir_parts_differs_when_only_destination_project_differs(
    tmp_path, monkeypatch
):
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
          organization_url: https://dev.azure.com/source-org
          project: OtherProject
          pat_env: DEST_PAT
        """
    )

    config = load_config(str(config_path))

    assert state_dir_parts(config) == [
        "source-org",
        "MyProject",
        "source-org",
        "OtherProject",
    ]


def test_state_dir_parts_sanitizes_unsafe_path_characters():
    from ado_migrate.config import MigrationConfig, OrgProjectConfig

    config = MigrationConfig(
        source=OrgProjectConfig(
            organization_url="https://dev.azure.com/My Org/",
            project="Team A/B",
            pat="s",
        ),
        destination=OrgProjectConfig(
            organization_url="https://dev.azure.com/Other Org",
            project="Team C",
            pat="d",
        ),
    )

    parts = state_dir_parts(config)

    assert all("/" not in part and " " not in part for part in parts)
