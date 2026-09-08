from ado_migrate.client import AdoClient
from ado_migrate.identity import UNMAPPED_PLACEHOLDER, IdentityMap
from ado_migrate.report import ReportSection
from ado_migrate.state import StateStore

ARTIFACT_TYPE = "security_groups"


def migrate_security_groups(
    source_client: AdoClient,
    dest_client: AdoClient,
    source_project: str,
    dest_project: str,
    state: StateStore,
    identity_map: IdentityMap,
) -> ReportSection:
    items = []
    existing_dest_group_ids = {
        g.id for g in dest_client.list_security_groups(dest_project)
    }

    for group in source_client.list_security_groups(source_project):
        resolved_members = []
        for identity in group.member_identities:
            resolved = identity_map.resolve(identity)
            if resolved == UNMAPPED_PLACEHOLDER:
                items.append(
                    f"{group.name}: {identity} has no destination mapping, skipped"
                )
            else:
                resolved_members.append(resolved)

        destination_id = state.get_destination_id(ARTIFACT_TYPE, source_id=group.id)
        already_exists = destination_id is not None and destination_id in existing_dest_group_ids

        if not already_exists:
            destination_group = dest_client.create_security_group(
                dest_project, group.name, resolved_members
            )

            if not dest_client.dry_run:
                state.mark_complete(
                    ARTIFACT_TYPE,
                    source_id=group.id,
                    destination_id=destination_group.id,
                )

        items.append(f"{group.name} ({len(resolved_members)} members)")

    return ReportSection(title="Security Groups", items=items)
