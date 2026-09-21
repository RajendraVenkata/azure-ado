from ado_migrate.client import AdoClient
from ado_migrate.git_transport import GitTransport
from ado_migrate.report import ReportSection
from ado_migrate.state import StateStore

ARTIFACT_TYPE = "wikis"


def migrate_wikis(
    source_client: AdoClient,
    dest_client: AdoClient,
    git_transport: GitTransport,
    source_project: str,
    dest_project: str,
    state: StateStore,
) -> ReportSection:
    items = []
    existing_dest_wikis = {w.name: w for w in dest_client.list_wikis(dest_project)}
    existing_dest_wiki_ids = {w.id for w in existing_dest_wikis.values()}

    for wiki in source_client.list_wikis(source_project):
        destination_id = state.get_destination_id(ARTIFACT_TYPE, source_id=wiki.id)
        already_exists = destination_id is not None and destination_id in existing_dest_wiki_ids
        note = ""

        if not already_exists:
            name_collision = existing_dest_wikis.get(wiki.name)

            if name_collision is not None:
                # A wiki with this name already exists in the destination but
                # wasn't created by this migration (no state record for it) —
                # creating it again fails with a duplicate-name error on the
                # backing repo, and mirror-pushing into it could overwrite
                # unrelated content, so just record the mapping and leave it
                # alone; its content must be reconciled manually.
                destination_id = name_collision.id
                note = " (already exists in destination, not pushed)"
            else:
                destination_repo = dest_client.create_wiki(dest_project, wiki.name)
                destination_url = (
                    destination_repo.clone_url if destination_repo is not None else None
                )
                git_transport.push_mirror(wiki.clone_url, destination_url)

                destination_wiki = None
                if destination_repo is not None:
                    # The wiki resource itself is only registered after its
                    # content has been pushed: Azure DevOps requires a code
                    # wiki's backing repo to already have a default branch,
                    # which doesn't exist until the mirror push above creates
                    # one.
                    destination_wiki = dest_client.publish_wiki(
                        dest_project, destination_repo.id, wiki.name
                    )
                destination_id = (
                    destination_wiki.id if destination_wiki is not None else None
                )

            if not dest_client.dry_run and destination_id is not None:
                state.mark_complete(
                    ARTIFACT_TYPE,
                    source_id=wiki.id,
                    destination_id=destination_id,
                )

        items.append(f"{wiki.name}{note}")

    return ReportSection(title="Wikis", items=items)
