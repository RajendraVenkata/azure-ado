from ado_migrate.client import AdoClient
from ado_migrate.report import ReportSection
from ado_migrate.state import StateStore

ARTIFACT_TYPE = "service_connections"


def migrate_service_connections(
    source_client: AdoClient,
    dest_client: AdoClient,
    source_project: str,
    dest_project: str,
    state: StateStore,
) -> ReportSection:
    items = []
    existing_dest_connection_ids = {
        c.id for c in dest_client.list_service_connections(dest_project)
    }

    for connection in source_client.list_service_connections(source_project):
        destination_id = state.get_destination_id(ARTIFACT_TYPE, source_id=connection.id)
        already_exists = (
            destination_id is not None and destination_id in existing_dest_connection_ids
        )

        if not already_exists:
            destination_connection = dest_client.create_service_connection(
                dest_project,
                connection.name,
                connection.connection_type,
                connection.config,
                has_secret=connection.has_secret,
            )

            if not dest_client.dry_run:
                state.mark_complete(
                    ARTIFACT_TYPE,
                    source_id=connection.id,
                    destination_id=destination_connection.id,
                )

        item = f"{connection.name} ({connection.connection_type})"
        if connection.has_secret:
            item += " - secret must be re-entered manually"
        items.append(item)

    return ReportSection(title="Service Connections", items=items)
