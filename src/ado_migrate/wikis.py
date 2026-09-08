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

    for wiki in source_client.list_wikis(source_project):
        if not state.is_complete(ARTIFACT_TYPE, source_id=wiki.id):
            destination_repo = dest_client.create_wiki(dest_project, wiki.name)
            destination_url = (
                destination_repo.clone_url if destination_repo is not None else None
            )
            git_transport.push_mirror(wiki.clone_url, destination_url)

            destination_wiki = None
            if destination_repo is not None:
                # The wiki resource itself is only registered after its
                # content has been pushed: Azure DevOps requires a code
                # wiki's backing repo to already have a default branch, which
                # doesn't exist until the mirror push above creates one.
                destination_wiki = dest_client.publish_wiki(
                    dest_project, destination_repo.id, wiki.name
                )

            if not dest_client.dry_run:
                state.mark_complete(
                    ARTIFACT_TYPE,
                    source_id=wiki.id,
                    destination_id=destination_wiki.id,
                )

        items.append(wiki.name)

    return ReportSection(title="Wikis", items=items)
