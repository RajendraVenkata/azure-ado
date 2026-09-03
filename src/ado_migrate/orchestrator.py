import logging
from typing import Optional

from ado_migrate.client import AdoClient
from ado_migrate.git_transport import GitTransport
from ado_migrate.identity import IdentityMap
from ado_migrate.links import rewrite_work_item_links
from ado_migrate.paths import migrate_area_paths, migrate_iteration_paths
from ado_migrate.pipelines import migrate_pipelines
from ado_migrate.queries import migrate_queries
from ado_migrate.report import ReportData, ReportSection
from ado_migrate.report_only import detect_report_only_artifacts
from ado_migrate.repos import migrate_repos
from ado_migrate.security_groups import migrate_security_groups
from ado_migrate.service_connections import migrate_service_connections
from ado_migrate.state import StateStore
from ado_migrate.test_plans import migrate_test_plans
from ado_migrate.wikis import migrate_wikis
from ado_migrate.work_items import migrate_work_items

logger = logging.getLogger(__name__)

ARTIFACT_TYPES_IN_ORDER = [
    "area_paths",
    "iteration_paths",
    "repos",
    "wikis",
    "service_connections",
    "work_items",
    "queries",
    "pipelines",
    "test_plans",
    "security_groups",
    "links",
    "report_only",
]


def run_migration(
    source_client: AdoClient,
    dest_client: AdoClient,
    git_transport: GitTransport,
    source_project: str,
    dest_project: str,
    state: StateStore,
    identity_map: IdentityMap,
    only: Optional[set[str]] = None,
) -> ReportData:
    types_to_run = only if only is not None else set(ARTIFACT_TYPES_IN_ORDER)

    sections: list[ReportSection] = []
    failures: list[str] = []

    for artifact_type in ARTIFACT_TYPES_IN_ORDER:
        if artifact_type not in types_to_run:
            continue

        logger.info("Starting %s", artifact_type)
        try:
            result = _run_step(
                artifact_type,
                source_client,
                dest_client,
                git_transport,
                source_project,
                dest_project,
                state,
                identity_map,
            )
            if isinstance(result, list):
                sections.extend(result)
            else:
                sections.append(result)
            logger.info("Completed %s", artifact_type)
        except Exception as e:
            logger.error("Failed %s: %s", artifact_type, e)
            state.record_failure(artifact_type, str(e))
            failures.append(f"{artifact_type}: {e}")

    if failures:
        sections.append(ReportSection(title="Failures", items=failures))

    return ReportData(dry_run=dest_client.dry_run, sections=sections)


def _run_step(
    artifact_type: str,
    source_client: AdoClient,
    dest_client: AdoClient,
    git_transport: GitTransport,
    source_project: str,
    dest_project: str,
    state: StateStore,
    identity_map: IdentityMap,
):
    if artifact_type == "area_paths":
        return migrate_area_paths(
            source_client, dest_client, source_project, dest_project, state
        )
    if artifact_type == "iteration_paths":
        return migrate_iteration_paths(
            source_client, dest_client, source_project, dest_project, state
        )
    if artifact_type == "repos":
        return migrate_repos(
            source_client, dest_client, git_transport, source_project, dest_project, state
        )
    if artifact_type == "wikis":
        return migrate_wikis(
            source_client, dest_client, git_transport, source_project, dest_project, state
        )
    if artifact_type == "service_connections":
        return migrate_service_connections(
            source_client, dest_client, source_project, dest_project, state
        )
    if artifact_type == "work_items":
        return migrate_work_items(
            source_client, dest_client, source_project, dest_project, state, identity_map
        )
    if artifact_type == "queries":
        return migrate_queries(
            source_client, dest_client, source_project, dest_project, state
        )
    if artifact_type == "pipelines":
        return migrate_pipelines(
            source_client, dest_client, source_project, dest_project, state
        )
    if artifact_type == "test_plans":
        return migrate_test_plans(
            source_client, dest_client, source_project, dest_project, state
        )
    if artifact_type == "security_groups":
        return migrate_security_groups(
            source_client, dest_client, source_project, dest_project, state, identity_map
        )
    if artifact_type == "links":
        return rewrite_work_item_links(
            source_client, dest_client, source_project, dest_project, state
        )
    if artifact_type == "report_only":
        return detect_report_only_artifacts(source_client, source_project)

    raise ValueError(f"Unknown artifact type: {artifact_type}")
