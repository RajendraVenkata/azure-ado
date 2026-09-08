from ado_migrate.client import Attachment, InMemoryFakeAdoClient, WorkItem
from ado_migrate.identity import UNMAPPED_PLACEHOLDER, IdentityMap
from ado_migrate.state import StateStore
from ado_migrate.work_items import migrate_work_items


def test_migrate_work_items_creates_single_revision_work_item(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_work_items(
        "SourceProject",
        [
            WorkItem(
                id="1",
                work_item_type="Bug",
                revisions=[{"Title": "Crash on save", "State": "New"}],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({})

    section = migrate_work_items(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    destination_id = state.get_destination_id("work_items", source_id="1")
    dest_item = dest.get_work_item("DestProject", destination_id)

    assert dest_item.revisions == [{"Title": "Crash on save", "State": "New"}]
    assert dest_item.work_item_type == "Bug"
    assert state.is_complete("work_items", source_id="1")
    assert "1" in section.items


def test_migrate_work_items_replays_every_revision_in_order(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_work_items(
        "SourceProject",
        [
            WorkItem(
                id="1",
                work_item_type="Bug",
                revisions=[
                    {"Title": "Crash on save", "State": "New"},
                    {"Title": "Crash on save", "State": "Active"},
                    {"Title": "Crash on save (fixed)", "State": "Resolved"},
                ],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({})

    migrate_work_items(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    destination_id = state.get_destination_id("work_items", source_id="1")
    dest_item = dest.get_work_item("DestProject", destination_id)

    assert dest_item.revisions == [
        {"Title": "Crash on save", "State": "New"},
        {"Title": "Crash on save", "State": "Active"},
        {"Title": "Crash on save (fixed)", "State": "Resolved"},
    ]


def test_migrate_work_items_resolves_assigned_to_through_identity_map(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_work_items(
        "SourceProject",
        [
            WorkItem(
                id="1",
                work_item_type="Bug",
                revisions=[{"Title": "Crash", "AssignedTo": "source.user@x.com"}],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({"source.user@x.com": "dest.user@y.com"})

    migrate_work_items(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    destination_id = state.get_destination_id("work_items", source_id="1")
    dest_item = dest.get_work_item("DestProject", destination_id)

    assert dest_item.revisions[0]["AssignedTo"] == "dest.user@y.com"


def test_migrate_work_items_leaves_assigned_to_unset_for_unknown_assignee(
    tmp_path,
):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_work_items(
        "SourceProject",
        [
            WorkItem(
                id="1",
                work_item_type="Bug",
                revisions=[{"Title": "Crash", "AssignedTo": "nobody@x.com"}],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({})

    migrate_work_items(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    destination_id = state.get_destination_id("work_items", source_id="1")
    dest_item = dest.get_work_item("DestProject", destination_id)

    assert "AssignedTo" not in dest_item.revisions[0]
    assert identity_map.resolved["nobody@x.com"] == UNMAPPED_PLACEHOLDER


def test_migrate_work_items_resolves_area_and_iteration_paths_from_state(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_work_items(
        "SourceProject",
        [
            WorkItem(
                id="1",
                work_item_type="Bug",
                revisions=[
                    {"Title": "Crash", "AreaPath": "Team A", "IterationPath": "Sprint 1"}
                ],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))
    state.mark_complete("area_paths", source_id="Team A", destination_id="Team A (dest)")
    state.mark_complete(
        "iteration_paths", source_id="Sprint 1", destination_id="Sprint 1 (dest)"
    )
    identity_map = IdentityMap({})

    migrate_work_items(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    destination_id = state.get_destination_id("work_items", source_id="1")
    dest_item = dest.get_work_item("DestProject", destination_id)

    assert dest_item.revisions[0]["AreaPath"] == "Team A (dest)"
    assert dest_item.revisions[0]["IterationPath"] == "Sprint 1 (dest)"


def test_migrate_work_items_keeps_original_path_when_no_mapping_exists(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_work_items(
        "SourceProject",
        [
            WorkItem(
                id="1",
                work_item_type="Bug",
                revisions=[{"Title": "Crash", "AreaPath": "Unmigrated Team"}],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({})

    migrate_work_items(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    destination_id = state.get_destination_id("work_items", source_id="1")
    dest_item = dest.get_work_item("DestProject", destination_id)

    assert dest_item.revisions[0]["AreaPath"] == "Unmigrated Team"


def test_migrate_work_items_migrates_attachment_content(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_work_items(
        "SourceProject",
        [
            WorkItem(
                id="1",
                work_item_type="Bug",
                revisions=[{"Title": "Crash"}],
                attachments=[Attachment(name="crash.log", content=b"stack trace")],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({})

    migrate_work_items(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    destination_id = state.get_destination_id("work_items", source_id="1")
    dest_item = dest.get_work_item("DestProject", destination_id)

    assert dest_item.attachments == [Attachment(name="crash.log", content=b"stack trace")]


def test_migrate_work_items_rerun_makes_no_additional_mutating_calls(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_work_items(
        "SourceProject",
        [WorkItem(id="1", work_item_type="Bug", revisions=[{"Title": "Crash"}])],
    )
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({})

    migrate_work_items(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )
    calls_after_first_run = len(dest.mutation_log)

    section = migrate_work_items(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    assert len(dest.mutation_log) == calls_after_first_run
    assert section.items == ["1"]


def test_migrate_work_items_resolves_identity_even_when_already_complete(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_work_items(
        "SourceProject",
        [
            WorkItem(
                id="1",
                work_item_type="Bug",
                revisions=[{"Title": "Crash", "AssignedTo": "alice@x.com"}],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))
    state.mark_complete("work_items", source_id="1", destination_id="wi-1")
    identity_map = IdentityMap({"alice@x.com": "alice@y.com"})

    migrate_work_items(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    assert identity_map.resolved == {"alice@x.com": "alice@y.com"}


def test_migrate_work_items_dry_run_reports_without_mutating(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=True)
    source.seed_work_items(
        "SourceProject",
        [WorkItem(id="1", work_item_type="Bug", revisions=[{"Title": "Crash"}])],
    )
    state = StateStore(str(tmp_path / "state.json"))
    identity_map = IdentityMap({})

    section = migrate_work_items(
        source, dest, "SourceProject", "DestProject", state, identity_map
    )

    assert section.items == ["1"]
    assert state.is_complete("work_items", source_id="1") is False
    assert all(not record.executed for record in dest.mutation_log)
