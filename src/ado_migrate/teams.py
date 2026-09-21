from ado_migrate.client import AdoClient
from ado_migrate.report import ReportSection
from ado_migrate.state import StateStore

ARTIFACT_TYPE = "teams"


def migrate_teams(
    source_client: AdoClient,
    dest_client: AdoClient,
    source_project: str,
    dest_project: str,
    state: StateStore,
) -> ReportSection:
    items = []
    existing_dest_teams = {t.name for t in dest_client.list_teams(dest_project)}

    for team in source_client.list_teams(source_project):
        iterations = source_client.list_team_iterations(source_project, team.name)
        area_paths = source_client.list_team_area_paths(source_project, team.name)

        destination_id = state.get_destination_id(ARTIFACT_TYPE, source_id=team.id)
        already_synced = destination_id is not None and destination_id in existing_dest_teams

        if not already_synced:
            pre_existing_team = team.name in existing_dest_teams
            if not pre_existing_team:
                dest_client.create_team(dest_project, team.name)

            for path in iterations:
                dest_client.add_team_iteration(dest_project, team.name, path)

            # A team that already existed in the destination (not created by
            # this migration) may have its own area path configuration;
            # set_team_area_paths() fully replaces that configuration, so
            # only apply it to teams this migration is creating.
            if not pre_existing_team:
                dest_client.set_team_area_paths(dest_project, team.name, area_paths)

            if not dest_client.dry_run:
                state.mark_complete(
                    ARTIFACT_TYPE, source_id=team.id, destination_id=team.name
                )

        items.append(
            f"{team.name} ({len(iterations)} iteration(s), {len(area_paths)} area path(s))"
        )

    return ReportSection(title="Teams", items=items)
