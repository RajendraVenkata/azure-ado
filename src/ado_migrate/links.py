from ado_migrate.client import AdoClient, Link
from ado_migrate.report import ReportSection
from ado_migrate.state import StateStore

WORK_ITEM_ARTIFACT_TYPE = "work_items"
REPO_ARTIFACT_TYPE = "repos"
LINK_REWRITE_ARTIFACT_TYPE = "link_rewrites"


def rewrite_work_item_links(
    source_client: AdoClient,
    dest_client: AdoClient,
    source_project: str,
    dest_project: str,
    state: StateStore,
) -> ReportSection:
    external = []

    for work_item in source_client.list_work_items(source_project):
        destination_id = state.get_destination_id(
            WORK_ITEM_ARTIFACT_TYPE, source_id=work_item.id
        )
        if destination_id is None or not work_item.links:
            continue

        resolved_links = []
        for link in work_item.links:
            resolved_link, is_external = _resolve_link(link, state)
            resolved_links.append(resolved_link)
            if is_external:
                external.append(f"{work_item.id} -> {link.target} ({link.link_type})")

        if not state.is_complete(LINK_REWRITE_ARTIFACT_TYPE, source_id=work_item.id):
            dest_client.update_work_item_links(
                dest_project, destination_id, resolved_links
            )
            if not dest_client.dry_run:
                state.mark_complete(
                    LINK_REWRITE_ARTIFACT_TYPE,
                    source_id=work_item.id,
                    destination_id=destination_id,
                )

    return ReportSection(title="External References Retained", items=external)


def _resolve_link(link: Link, state: StateStore) -> tuple[Link, bool]:
    if link.link_type == "work_item":
        target_destination_id = state.get_destination_id(
            WORK_ITEM_ARTIFACT_TYPE, source_id=link.target
        )
        if target_destination_id is not None:
            return Link(link_type=link.link_type, target=target_destination_id), False
        return link, True

    if link.link_type == "pull_request":
        repo_id, _, pr_number = link.target.partition(":")
        destination_repo_id = state.get_destination_id(
            REPO_ARTIFACT_TYPE, source_id=repo_id
        )
        if destination_repo_id is not None:
            return (
                Link(link_type=link.link_type, target=f"{destination_repo_id}:{pr_number}"),
                False,
            )
        return link, True

    return link, True
