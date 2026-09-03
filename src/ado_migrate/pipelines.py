from ado_migrate.client import AdoClient
from ado_migrate.report import ReportSection
from ado_migrate.state import StateStore

ARTIFACT_TYPE = "pipelines"


def migrate_pipelines(
    source_client: AdoClient,
    dest_client: AdoClient,
    source_project: str,
    dest_project: str,
    state: StateStore,
) -> ReportSection:
    items = []

    for pipeline in source_client.list_pipelines(source_project):
        if not state.is_complete(ARTIFACT_TYPE, source_id=pipeline.id):
            resolved_repo_id = _resolve(pipeline.repo_id, "repos", state)
            resolved_service_connection_ids = [
                _resolve(sc_id, "service_connections", state)
                for sc_id in pipeline.service_connection_ids
            ]

            destination_pipeline = dest_client.create_pipeline(
                dest_project,
                pipeline.name,
                pipeline.yaml_path,
                resolved_repo_id,
                resolved_service_connection_ids,
            )

            if not dest_client.dry_run:
                state.mark_complete(
                    ARTIFACT_TYPE,
                    source_id=pipeline.id,
                    destination_id=destination_pipeline.id,
                )

        items.append(pipeline.name)

    return ReportSection(title="Pipelines", items=items)


def _resolve(source_id: str, artifact_type: str, state: StateStore) -> str:
    destination_id = state.get_destination_id(artifact_type, source_id=source_id)
    return destination_id if destination_id is not None else source_id
