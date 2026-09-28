import logging

from ado_migrate.client import AdoClient, DEFAULT_SECURITY_GROUP_NAMES, SecurityGroup
from ado_migrate.identity import UNMAPPED_PLACEHOLDER, IdentityMap
from ado_migrate.report import ReportSection
from ado_migrate.state import StateStore

logger = logging.getLogger(__name__)

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
    existing_dest_groups = {
        g.name: g for g in dest_client.list_security_groups(dest_project)
    }
    existing_dest_group_ids = {g.id for g in existing_dest_groups.values()}

    for group in source_client.list_security_groups(source_project):
        resolved_members = []
        for identity in group.member_identities:
            resolved = identity_map.resolve(identity)
            if resolved == UNMAPPED_PLACEHOLDER:
                items.append(
                    f"{group.name}: {identity} has no destination mapping, skipped"
                )
                logger.warning(
                    "'%s' has no destination mapping; not assigned to '%s'",
                    identity,
                    group.name,
                )
            else:
                resolved_members.append(resolved)

        if group.name in DEFAULT_SECURITY_GROUP_NAMES:
            member_count = _sync_default_group(
                dest_client, dest_project, group, resolved_members, existing_dest_groups, items
            )
        else:
            member_count = _sync_custom_group(
                dest_client,
                dest_project,
                group,
                resolved_members,
                state,
                existing_dest_group_ids,
                items,
            )

        items.append(f"{group.name} ({member_count} members)")
        logger.info(
            "Security group '%s': %d of %d resolved member(s) assigned in %s",
            group.name,
            member_count,
            len(resolved_members),
            dest_project,
        )

    return ReportSection(title="Security Groups", items=items)


def _sync_default_group(
    dest_client: AdoClient,
    dest_project: str,
    group: SecurityGroup,
    resolved_members: list[str],
    existing_dest_groups: dict[str, SecurityGroup],
    items: list[str],
) -> int:
    """Built-in groups (Contributors, Readers, ...) already exist in every
    project — mirror the source group's actual membership onto the
    same-named destination group instead of dumping every migrated user
    into a single group regardless of their source role."""
    dest_group = existing_dest_groups.get(group.name)
    if dest_group is None:
        if resolved_members:
            items.append(f"{group.name}: not found in the destination project, skipped")
            logger.warning(
                "Built-in group '%s' not found in destination project '%s'; "
                "%d resolved member(s) not assigned",
                group.name,
                dest_project,
                len(resolved_members),
            )
        return 0

    to_add = [m for m in resolved_members if m not in dest_group.member_identities]
    if not to_add or dest_client.dry_run:
        return len(resolved_members)

    added = dest_client.add_group_members(dest_project, dest_group.id, group.name, to_add)
    for identity in to_add:
        if identity not in added:
            items.append(
                f"{group.name}: {identity} could not be added in the destination "
                "organization (identity not found), skipped"
            )
    return len(resolved_members) - (len(to_add) - len(added))


def _sync_custom_group(
    dest_client: AdoClient,
    dest_project: str,
    group: SecurityGroup,
    resolved_members: list[str],
    state: StateStore,
    existing_dest_group_ids: set[str],
    items: list[str],
) -> int:
    destination_id = state.get_destination_id(ARTIFACT_TYPE, source_id=group.id)
    already_exists = destination_id is not None and destination_id in existing_dest_group_ids

    if already_exists:
        return len(resolved_members)

    destination_group = dest_client.create_security_group(
        dest_project, group.name, resolved_members
    )

    if dest_client.dry_run:
        return len(resolved_members)

    state.mark_complete(
        ARTIFACT_TYPE,
        source_id=group.id,
        destination_id=destination_group.id,
    )

    # create_security_group() only returns the members it actually
    # confirmed adding — a resolved destination identity can still fail to
    # add if it doesn't exist in the destination org's directory. Surface
    # that gap instead of reporting a member count nothing verified.
    added_members = destination_group.member_identities
    for identity in resolved_members:
        if identity not in added_members:
            items.append(
                f"{group.name}: {identity} could not be added in the destination "
                "organization (identity not found), skipped"
            )
    return len(added_members)
