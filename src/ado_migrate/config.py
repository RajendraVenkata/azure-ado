import os
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
