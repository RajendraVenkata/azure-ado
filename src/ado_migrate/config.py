import os
import re
from dataclasses import dataclass

import yaml


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class OrgProjectConfig:
    organization_url: str
    project: str
    pat: str


@dataclass(frozen=True)
class MigrationConfig:
    source: OrgProjectConfig
    destination: OrgProjectConfig


def load_config(path: str) -> MigrationConfig:
    with open(path) as f:
        raw = yaml.safe_load(f)

    return MigrationConfig(
        source=_load_org_project(raw["source"]),
        destination=_load_org_project(raw["destination"]),
    )


def _load_org_project(raw: dict) -> OrgProjectConfig:
    pat_env = raw["pat_env"]
    pat = os.environ.get(pat_env)
    if pat is None:
        raise ConfigError(
            f"Environment variable '{pat_env}' referenced by pat_env is not set"
        )

    return OrgProjectConfig(
        organization_url=raw["organization_url"],
        project=raw["project"],
        pat=pat,
    )


def state_dir_parts(config: MigrationConfig) -> list[str]:
    """Path segments uniquely identifying this source/destination pair, so
    state from different migration pairs never collides on disk even when
    they share a config directory."""
    return [
        _path_segment(_org_name(config.source.organization_url)),
        _path_segment(config.source.project),
        _path_segment(_org_name(config.destination.organization_url)),
        _path_segment(config.destination.project),
    ]


def _org_name(organization_url: str) -> str:
    return organization_url.rstrip("/").rsplit("/", 1)[-1]


def _path_segment(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-")
    return sanitized or "unknown"
