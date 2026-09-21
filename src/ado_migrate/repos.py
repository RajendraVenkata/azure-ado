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
    existing_dest_repos = {r.name: r for r in dest_client.list_repos(dest_project)}
    existing_dest_repo_ids = {r.id for r in existing_dest_repos.values()}

    for repo in source_client.list_repos(source_project):
        destination_id = state.get_destination_id(ARTIFACT_TYPE, source_id=repo.id)
        already_exists = destination_id is not None and destination_id in existing_dest_repo_ids
        note = ""

        if not already_exists:
            name_collision = existing_dest_repos.get(repo.name)

            if name_collision is not None:
                # A repo with this name already exists in the destination but
                # wasn't created by this migration (no state record for it) —
                # creating it again fails with a duplicate-name error, and
                # mirror-pushing into it could overwrite unrelated content, so
                # just record the mapping and leave it alone; its content
                # must be reconciled manually.
                destination_id = name_collision.id
                note = " (already exists in destination, not pushed)"
            else:
                destination_repo = dest_client.create_repo(dest_project, repo.name)
                destination_url = (
                    destination_repo.clone_url if destination_repo is not None else None
                )
                git_transport.push_mirror(repo.clone_url, destination_url)
                destination_id = (
                    destination_repo.id if destination_repo is not None else None
                )

            if not dest_client.dry_run and destination_id is not None:
                state.mark_complete(
                    ARTIFACT_TYPE,
                    source_id=repo.id,
                    destination_id=destination_id,
                )

        items.append(f"{repo.name}{note}")

    return ReportSection(title="Repositories", items=items)
