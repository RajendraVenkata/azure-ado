from ado_migrate.client import AdoClient
from ado_migrate.report import ReportSection
from ado_migrate.state import StateStore

AREA_ARTIFACT_TYPE = "area_paths"
ITERATION_ARTIFACT_TYPE = "iteration_paths"


def migrate_area_paths(
    source_client: AdoClient,
    dest_client: AdoClient,
    source_project: str,
    dest_project: str,
    state: StateStore,
) -> ReportSection:
    source_paths = _parent_first(source_client.list_area_paths(source_project))
    existing_dest_paths = set(dest_client.list_area_paths(dest_project))

    items = []
    for path in source_paths:
        if not state.is_complete(AREA_ARTIFACT_TYPE, source_id=path):
            if path in existing_dest_paths:
                destination_id = path
            else:
                destination_id = dest_client.create_area_path(dest_project, path)

            if not dest_client.dry_run:
                state.mark_complete(
                    AREA_ARTIFACT_TYPE, source_id=path, destination_id=destination_id
                )
        items.append(path)

    return ReportSection(title="Area Paths", items=items)


def _parent_first(paths: list[str]) -> list[str]:
    return sorted(paths, key=lambda path: path.count("/"))


def migrate_iteration_paths(
    source_client: AdoClient,
    dest_client: AdoClient,
    source_project: str,
    dest_project: str,
    state: StateStore,
) -> ReportSection:
    source_paths = sorted(
        source_client.list_iteration_paths(source_project),
        key=lambda iteration: iteration.path.count("/"),
    )
    existing_dest_paths = {p.path for p in dest_client.list_iteration_paths(dest_project)}

    items = []
    for iteration in source_paths:
        if not state.is_complete(ITERATION_ARTIFACT_TYPE, source_id=iteration.path):
            if iteration.path in existing_dest_paths:
                destination_id = iteration.path
            else:
                destination_id = dest_client.create_iteration_path(
                    dest_project,
                    iteration.path,
                    start_date=iteration.start_date,
                    end_date=iteration.end_date,
                )

            if not dest_client.dry_run:
                state.mark_complete(
                    ITERATION_ARTIFACT_TYPE,
                    source_id=iteration.path,
                    destination_id=destination_id,
                )
        items.append(iteration.path)

    return ReportSection(title="Iteration Paths", items=items)
