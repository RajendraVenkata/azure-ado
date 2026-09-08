from ado_migrate.client import AdoClient
from ado_migrate.git_transport import GitTransport
from ado_migrate.report import ReportSection
from ado_migrate.state import StateStore

ARTIFACT_TYPE = "repos"


def migrate_repos(
    source_client: AdoClient,
    dest_client: AdoClient,
    git_transport: GitTransport,
    source_project: str,
    dest_project: str,
    state: StateStore,
) -> ReportSection:
    items = []
    existing_dest_repo_ids = {r.id for r in dest_client.list_repos(dest_project)}

    for repo in source_client.list_repos(source_project):
        destination_id = state.get_destination_id(ARTIFACT_TYPE, source_id=repo.id)
        already_exists = destination_id is not None and destination_id in existing_dest_repo_ids

        if not already_exists:
            destination_repo = dest_client.create_repo(dest_project, repo.name)
            destination_url = (
                destination_repo.clone_url if destination_repo is not None else None
            )
            git_transport.push_mirror(repo.clone_url, destination_url)

            if not dest_client.dry_run:
                state.mark_complete(
                    ARTIFACT_TYPE,
                    source_id=repo.id,
                    destination_id=destination_repo.id,
                )

        items.append(repo.name)

    return ReportSection(title="Repositories", items=items)
