from ado_migrate.client import AdoClient
from ado_migrate.identity import UNMAPPED_PLACEHOLDER, IdentityMap, format_resolution
from ado_migrate.report import ReportSection
from ado_migrate.state import StateStore

ARTIFACT_TYPE = "users"


def migrate_users(
    source_client: AdoClient,
    dest_client: AdoClient,
    source_project: str,
    dest_project: str,
    state: StateStore,
    identity_map: IdentityMap,
) -> ReportSection:
    """Report the identities with project-level permissions in the source
    project (Project Settings > Permissions > Users), resolved through the
    identity map, and add each resolved identity as a member of the
    destination project so their access actually carries over. Identities
    with no destination mapping are reported but left for manual follow-up
    — there is nothing to add them as."""
    identities = sorted(set(source_client.list_project_users(source_project)))
    items = []
    existing_dest_members = set(dest_client.list_project_members(dest_project))

    for identity in identities:
        destination_identity = identity_map.resolve(identity)
        items.append(format_resolution(identity, destination_identity))

        if destination_identity == UNMAPPED_PLACEHOLDER:
            continue

        recorded_id = state.get_destination_id(ARTIFACT_TYPE, source_id=identity)
        already_member = recorded_id is not None and recorded_id in existing_dest_members

        if not already_member:
            dest_client.add_project_member(dest_project, destination_identity)

            if not dest_client.dry_run:
                state.mark_complete(
                    ARTIFACT_TYPE,
                    source_id=identity,
                    destination_id=destination_identity,
                )

    return ReportSection(title="Users", items=items)
