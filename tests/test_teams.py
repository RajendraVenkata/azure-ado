from ado_migrate.client import InMemoryFakeAdoClient, Team, TeamAreaPath
from ado_migrate.state import StateStore
from ado_migrate.teams import migrate_teams


def test_migrate_teams_creates_team_with_iterations_and_area_paths(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_teams("SourceProject", [Team(id="team-1", name="Alpha Team")])
    source.seed_team_iterations(
        "SourceProject", "Alpha Team", ["Release 1/Sprint 1", "Release 1/Sprint 2"]
    )
    source.seed_team_area_paths(
        "SourceProject",
        "Alpha Team",
        [TeamAreaPath(path="Team A", include_children=True)],
    )
    state = StateStore(str(tmp_path / "state.json"))

    section = migrate_teams(source, dest, "SourceProject", "DestProject", state)

    dest_teams = dest.list_teams("DestProject")
    assert len(dest_teams) == 1
    assert dest_teams[0].name == "Alpha Team"
    assert dest.list_team_iterations("DestProject", "Alpha Team") == [
        "Release 1/Sprint 1",
        "Release 1/Sprint 2",
    ]
    assert dest.list_team_area_paths("DestProject", "Alpha Team") == [
        TeamAreaPath(path="Team A", include_children=True)
    ]
    assert state.is_complete("teams", source_id="team-1")
    assert section.items == ["Alpha Team (2 iteration(s), 1 area path(s))"]


def test_migrate_teams_reuses_existing_destination_team(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_teams("SourceProject", [Team(id="team-1", name="Alpha Team")])
    dest.seed_teams("DestProject", [Team(id="existing-team", name="Alpha Team")])
    state = StateStore(str(tmp_path / "state.json"))

    migrate_teams(source, dest, "SourceProject", "DestProject", state)

    assert len(dest.list_teams("DestProject")) == 1


def test_migrate_teams_dry_run_reports_without_mutating(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=True)
    source.seed_teams("SourceProject", [Team(id="team-1", name="Alpha Team")])
    source.seed_team_iterations("SourceProject", "Alpha Team", ["Sprint 1"])
    state = StateStore(str(tmp_path / "state.json"))

    section = migrate_teams(source, dest, "SourceProject", "DestProject", state)

    assert section.items == ["Alpha Team (1 iteration(s), 0 area path(s))"]
    assert dest.list_teams("DestProject") == []
    assert state.is_complete("teams", source_id="team-1") is False
    assert all(not record.executed for record in dest.mutation_log)


def test_migrate_teams_rerun_makes_no_additional_mutating_calls(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_teams("SourceProject", [Team(id="team-1", name="Alpha Team")])
    source.seed_team_iterations("SourceProject", "Alpha Team", ["Sprint 1"])
    state = StateStore(str(tmp_path / "state.json"))

    migrate_teams(source, dest, "SourceProject", "DestProject", state)
    calls_after_first_run = len(dest.mutation_log)

    section = migrate_teams(source, dest, "SourceProject", "DestProject", state)

    assert len(dest.mutation_log) == calls_after_first_run
    assert section.items == ["Alpha Team (1 iteration(s), 0 area path(s))"]
