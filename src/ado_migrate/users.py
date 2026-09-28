from ado_migrate.client import AdoClient
from ado_migrate.identity import IdentityMap, format_resolution
from ado_migrate.report import ReportSection


def migrate_users(
    source_client: AdoClient,
    source_project: str,
    identity_map: IdentityMap,
) -> ReportSection:
    """Report the identities with project-level permissions in the source
    project (Project Settings > Permissions > Users), resolved through the
    identity map. This step is reporting-only: destination project access
    is granted per security group by migrate_security_groups(), which
    replicates each user's actual built-in (Readers/Contributors/Project
    Administrators/...) and custom group membership from the source —
    rather than every project user being dumped into a single destination
    group regardless of their source role."""
    identities = sorted(set(source_client.list_project_users(source_project)))
    items = [
        format_resolution(identity, identity_map.resolve(identity))
        for identity in identities
    ]
    return ReportSection(title="Users", items=items)
