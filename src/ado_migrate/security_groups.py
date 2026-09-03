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

        if not state.is_complete(ARTIFACT_TYPE, source_id=group.id):
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
