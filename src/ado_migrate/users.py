import logging

from ado_migrate.client import AdoClient
from ado_migrate.identity import UNMAPPED_PLACEHOLDER, IdentityMap, format_resolution
from ado_migrate.report import ReportSection

logger = logging.getLogger(__name__)


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
    logger.info(
        "Resolving %d distinct project user(s) from '%s' through the identity map",
        len(identities),
        source_project,
    )

    items = []
    unmapped_count = 0
    for identity in identities:
        destination_identity = identity_map.resolve(identity)
        items.append(format_resolution(identity, destination_identity))
        if destination_identity == UNMAPPED_PLACEHOLDER:
            unmapped_count += 1
            logger.warning("'%s' has no destination mapping in identity.yaml", identity)
        else:
            logger.info("'%s' resolves to '%s'", identity, destination_identity)

    if unmapped_count:
        logger.warning(
            "%d of %d project user(s) have no destination mapping", unmapped_count, len(identities)
        )

    return ReportSection(title="Users", items=items)
