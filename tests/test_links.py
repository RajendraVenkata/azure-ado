from ado_migrate.client import InMemoryFakeAdoClient, Link, WorkItem
from ado_migrate.links import rewrite_work_item_links
from ado_migrate.state import StateStore


def test_rewrite_work_item_links_rewrites_link_to_migrated_work_item(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_work_items(
        "SourceProject",
        [
            WorkItem(
                id="1",
                work_item_type="Bug",
                revisions=[{"Title": "A"}],
                links=[Link(link_type="work_item", target="2")],
            ),
            WorkItem(id="2", work_item_type="Task", revisions=[{"Title": "B"}]),
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))
    dest_item_1 = dest.create_work_item("DestProject", "Bug", {"Title": "A"})
    dest_item_2 = dest.create_work_item("DestProject", "Task", {"Title": "B"})
    state.mark_complete("work_items", source_id="1", destination_id=dest_item_1)
    state.mark_complete("work_items", source_id="2", destination_id=dest_item_2)

    section = rewrite_work_item_links(
        source, dest, "SourceProject", "DestProject", state
    )

    dest_wi1 = dest.get_work_item("DestProject", dest_item_1)
    assert dest_wi1.links == [Link(link_type="work_item", target=dest_item_2)]
    assert section.items == []


def test_rewrite_work_item_links_omits_link_to_out_of_scope_work_item(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_work_items(
        "SourceProject",
        [
            WorkItem(
                id="1",
                work_item_type="Bug",
                revisions=[{"Title": "A"}],
                links=[Link(link_type="work_item", target="999")],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))
    dest_item_1 = dest.create_work_item("DestProject", "Bug", {"Title": "A"})
    state.mark_complete("work_items", source_id="1", destination_id=dest_item_1)

    section = rewrite_work_item_links(
        source, dest, "SourceProject", "DestProject", state
    )

    dest_wi1 = dest.get_work_item("DestProject", dest_item_1)
    assert dest_wi1.links == []
    assert section.items == ["1 -> 999 (work_item)"]


def test_rewrite_work_item_links_rewrites_pull_request_link_to_migrated_repo(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_work_items(
        "SourceProject",
        [
            WorkItem(
                id="1",
                work_item_type="Bug",
                revisions=[{"Title": "A"}],
                links=[Link(link_type="pull_request", target="repo-1:42")],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))
    dest_item_1 = dest.create_work_item("DestProject", "Bug", {"Title": "A"})
    state.mark_complete("work_items", source_id="1", destination_id=dest_item_1)
    state.mark_complete("repos", source_id="repo-1", destination_id="repo-9")

    section = rewrite_work_item_links(
        source, dest, "SourceProject", "DestProject", state
    )

    dest_wi1 = dest.get_work_item("DestProject", dest_item_1)
    assert dest_wi1.links == [Link(link_type="pull_request", target="repo-9:42")]
    assert section.items == []


def test_rewrite_work_item_links_omits_pull_request_link_to_unmigrated_repo(
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
                revisions=[{"Title": "A"}],
                links=[Link(link_type="pull_request", target="repo-1:42")],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))
    dest_item_1 = dest.create_work_item("DestProject", "Bug", {"Title": "A"})
    state.mark_complete("work_items", source_id="1", destination_id=dest_item_1)

    section = rewrite_work_item_links(
        source, dest, "SourceProject", "DestProject", state
    )

    dest_wi1 = dest.get_work_item("DestProject", dest_item_1)
    assert dest_wi1.links == []
    assert section.items == ["1 -> repo-1:42 (pull_request)"]


def test_rewrite_work_item_links_rerun_makes_no_additional_mutating_calls(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_work_items(
        "SourceProject",
        [
            WorkItem(
                id="1",
                work_item_type="Bug",
                revisions=[{"Title": "A"}],
                links=[Link(link_type="work_item", target="999")],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))
    dest_item_1 = dest.create_work_item("DestProject", "Bug", {"Title": "A"})
    state.mark_complete("work_items", source_id="1", destination_id=dest_item_1)

    rewrite_work_item_links(source, dest, "SourceProject", "DestProject", state)
    calls_after_first_run = len(dest.mutation_log)

    section = rewrite_work_item_links(
        source, dest, "SourceProject", "DestProject", state
    )

    assert len(dest.mutation_log) == calls_after_first_run
    assert section.items == ["1 -> 999 (work_item)"]
