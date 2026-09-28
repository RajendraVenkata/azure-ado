import logging
from typing import Optional

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
    existing_dest_groups_by_id = {g.id: g for g in existing_dest_groups.values()}

    source_groups = source_client.list_security_groups(source_project)
    dest_group_id_by_source_name: dict[str, str] = {}

    for group in source_groups:
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
            dest_group = existing_dest_groups.get(group.name)
            if dest_group is not None:
                dest_group_id_by_source_name[group.name] = dest_group.id
        else:
            member_count, destination_id = _sync_custom_group(
                dest_client,
                dest_project,
                group,
                resolved_members,
                state,
                existing_dest_groups_by_id,
                items,
            )
            if destination_id is not None:
                dest_group_id_by_source_name[group.name] = destination_id

        items.append(f"{group.name} ({member_count} members)")
        logger.info(
            "Security group '%s': %d of %d resolved member(s) assigned in %s",
            group.name,
            member_count,
            len(resolved_members),
            dest_project,
        )

    _link_nested_groups(dest_client, dest_project, source_groups, dest_group_id_by_source_name, items)

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
    existing_dest_groups_by_id: dict[str, SecurityGroup],
    items: list[str],
) -> tuple[int, Optional[str]]:
    destination_id = state.get_destination_id(ARTIFACT_TYPE, source_id=group.id)
    dest_group = existing_dest_groups_by_id.get(destination_id) if destination_id else None

    if dest_group is not None:
        # The group itself already exists — but a member removed from it
        # in the destination since the last run (by hand, or by anything
        # else) would otherwise never be reconciled: this only ran once,
        # at creation time. Diff and re-add what's missing every run,
        # same as the built-in-group path.
        to_add = [m for m in resolved_members if m not in dest_group.member_identities]
        if not to_add or dest_client.dry_run:
            return len(resolved_members), destination_id

        added = dest_client.add_group_members(dest_project, dest_group.id, group.name, to_add)
        for identity in to_add:
            if identity not in added:
                items.append(
                    f"{group.name}: {identity} could not be added in the destination "
                    "organization (identity not found), skipped"
                )
        return len(resolved_members) - (len(to_add) - len(added)), destination_id

    destination_group = dest_client.create_security_group(
        dest_project, group.name, resolved_members
    )

    if dest_client.dry_run:
        return len(resolved_members), None

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
    return len(added_members), destination_group.id


def _link_nested_groups(
    dest_client: AdoClient,
    dest_project: str,
    source_groups: list[SecurityGroup],
    dest_group_id_by_source_name: dict[str, str],
    items: list[str],
) -> None:
    """Re-nest a group-to-group membership found in the source — an Azure
    DevOps-native group directly nested inside another (e.g. a project
    team's group nested inside Contributors) — onto the destination's own
    recreated copies of both groups, instead of leaving it flattened into
    individual users."""
    for group in source_groups:
        if not group.member_group_names:
            continue

        parent_dest_id = dest_group_id_by_source_name.get(group.name)
        for child_name in group.member_group_names:
            if dest_client.dry_run:
                items.append(f"{group.name}: would nest '{child_name}' under it (dry run)")
                continue

            child_dest_id = dest_group_id_by_source_name.get(child_name)
            if parent_dest_id is None or child_dest_id is None:
                items.append(
                    f"{group.name}: nested group '{child_name}' could not be linked "
                    "in the destination, skipped"
                )
                continue

            linked = dest_client.add_group_to_group(
                dest_project, parent_dest_id, group.name, child_dest_id, child_name
            )
            if not linked:
                items.append(
                    f"{group.name}: nested group '{child_name}' could not be linked "
                    "in the destination, skipped"
                )
