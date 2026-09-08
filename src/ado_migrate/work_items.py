from ado_migrate.client import AdoClient
from ado_migrate.identity import UNMAPPED_PLACEHOLDER, IdentityMap
from ado_migrate.report import ReportSection
from ado_migrate.state import StateStore

ARTIFACT_TYPE = "work_items"


def migrate_work_items(
    source_client: AdoClient,
    dest_client: AdoClient,
    source_project: str,
    dest_project: str,
    state: StateStore,
    identity_map: IdentityMap,
) -> ReportSection:
    items = []

    for work_item in source_client.list_work_items(source_project):
        resolved_revisions = [
            _resolve_fields(fields, identity_map, state)
            for fields in work_item.revisions
        ]

        if not state.is_complete(ARTIFACT_TYPE, source_id=work_item.id):
            first_fields, *later_revisions = resolved_revisions
            destination_id = dest_client.create_work_item(
                dest_project, work_item.work_item_type, first_fields
            )

            for revision_fields in later_revisions:
                dest_client.update_work_item_fields(
                    dest_project, destination_id, revision_fields
                )

            for attachment in work_item.attachments:
                dest_client.add_attachment(dest_project, destination_id, attachment)

            if not dest_client.dry_run:
                state.mark_complete(
                    ARTIFACT_TYPE,
                    source_id=work_item.id,
                    destination_id=destination_id,
                )

        items.append(work_item.id)

    return ReportSection(title="Work Items", items=items)


def _resolve_fields(fields: dict, identity_map: IdentityMap, state: StateStore) -> dict:
    resolved = dict(fields)
    if "AssignedTo" in resolved:
        destination_identity = identity_map.resolve(resolved["AssignedTo"])
        if destination_identity == UNMAPPED_PLACEHOLDER:
            # Azure DevOps validates AssignedTo against real identities and
            # rejects the placeholder outright, so leave the field unset
            # rather than fail the whole work item; the unmapped identity is
            # still surfaced via the Users report section.
            del resolved["AssignedTo"]
        else:
            resolved["AssignedTo"] = destination_identity
    if "AreaPath" in resolved:
        resolved["AreaPath"] = _resolve_path(resolved["AreaPath"], "area_paths", state)
    if "IterationPath" in resolved:
        resolved["IterationPath"] = _resolve_path(
            resolved["IterationPath"], "iteration_paths", state
        )
    return resolved


def _resolve_path(source_path: str, artifact_type: str, state: StateStore) -> str:
    destination_id = state.get_destination_id(artifact_type, source_id=source_path)
    return destination_id if destination_id is not None else source_path
