from ado_migrate.client import AdoClient
from ado_migrate.identity import IdentityMap, format_resolution
from ado_migrate.report import ReportSection

ARTIFACT_TYPE = "users"


def migrate_users(
    source_client: AdoClient,
    source_project: str,
    identity_map: IdentityMap,
) -> ReportSection:
    """Report the identities with project-level permissions in the source
    project (Project Settings > Permissions > Users), each resolved through
    the identity map to its destination identity."""
    identities = sorted(set(source_client.list_project_users(source_project)))
    items = [
        format_resolution(identity, identity_map.resolve(identity))
        for identity in identities
    ]

    return ReportSection(title="Users", items=items)
