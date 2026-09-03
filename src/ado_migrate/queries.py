from ado_migrate.client import AdoClient
from ado_migrate.report import ReportSection
from ado_migrate.state import StateStore

ARTIFACT_TYPE = "queries"


def migrate_queries(
    source_client: AdoClient,
    dest_client: AdoClient,
    source_project: str,
    dest_project: str,
    state: StateStore,
) -> ReportSection:
    items = []
    path_mappings = {
        **state.list_destination_ids("area_paths"),
        **state.list_destination_ids("iteration_paths"),
    }

    for query in source_client.list_queries(source_project):
        if not state.is_complete(ARTIFACT_TYPE, source_id=query.id):
            rewritten_wiql = _rewrite_paths(query.wiql, path_mappings)
            destination_query = dest_client.create_query(
                dest_project, query.name, query.folder_path, rewritten_wiql
            )

            if not dest_client.dry_run:
                state.mark_complete(
                    ARTIFACT_TYPE,
                    source_id=query.id,
                    destination_id=destination_query.id,
                )

        items.append(query.name)

    return ReportSection(title="Queries", items=items)


def _rewrite_paths(wiql: str, path_mappings: dict[str, str]) -> str:
    for source_path, destination_path in path_mappings.items():
        wiql = wiql.replace(f"'{source_path}'", f"'{destination_path}'")
    return wiql
