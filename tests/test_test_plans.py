from ado_migrate.client import InMemoryFakeAdoClient, TestPlan, TestSuite
from ado_migrate.state import StateStore
from ado_migrate.test_plans import migrate_test_plans


def test_migrate_test_plans_creates_plan_with_single_suite(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_test_plans(
        "SourceProject",
        [
            TestPlan(
                id="tp-1",
                name="Release 1 Test Plan",
                suites=[
                    TestSuite(
                        id="ts-1",
                        name="Smoke Tests",
                        test_case_ids=["wi-100"],
                        configuration_names=["Windows 10 + Chrome"],
                    )
                ],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))

    section = migrate_test_plans(
        source, dest, "SourceProject", "DestProject", state
    )

    destination_plan_id = state.get_destination_id("test_plans", source_id="tp-1")
    dest_plan = dest.get_test_plan("DestProject", destination_plan_id)

    assert dest_plan.name == "Release 1 Test Plan"
    assert len(dest_plan.suites) == 1
    assert dest_plan.suites[0].name == "Smoke Tests"
    assert dest_plan.suites[0].test_case_ids == ["wi-100"]
    assert dest_plan.suites[0].configuration_names == ["Windows 10 + Chrome"]
    assert dest_plan.suites[0].parent_suite_id is None

    assert state.is_complete("test_plans", source_id="tp-1")
    assert "Release 1 Test Plan" in section.items


def test_migrate_test_plans_creates_parent_suites_before_children(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_test_plans(
        "SourceProject",
        [
            TestPlan(
                id="tp-1",
                name="Release 1 Test Plan",
                suites=[
                    TestSuite(id="ts-child", name="Regression", parent_suite_id="ts-root"),
                    TestSuite(id="ts-root", name="Root Suite"),
                ],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))

    migrate_test_plans(source, dest, "SourceProject", "DestProject", state)

    destination_plan_id = state.get_destination_id("test_plans", source_id="tp-1")
    dest_plan = dest.get_test_plan("DestProject", destination_plan_id)

    names_in_order = [s.name for s in dest_plan.suites]
    assert names_in_order == ["Root Suite", "Regression"]

    root_destination_id = dest_plan.suites[0].id
    assert dest_plan.suites[1].parent_suite_id == root_destination_id


def test_migrate_test_plans_resolves_test_case_ids_through_work_item_mapping(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_test_plans(
        "SourceProject",
        [
            TestPlan(
                id="tp-1",
                name="Release 1 Test Plan",
                suites=[TestSuite(id="ts-1", name="Smoke Tests", test_case_ids=["1"])],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))
    state.mark_complete("work_items", source_id="1", destination_id="wi-9")

    migrate_test_plans(source, dest, "SourceProject", "DestProject", state)

    destination_plan_id = state.get_destination_id("test_plans", source_id="tp-1")
    dest_plan = dest.get_test_plan("DestProject", destination_plan_id)

    assert dest_plan.suites[0].test_case_ids == ["wi-9"]


def test_migrate_test_plans_rerun_makes_no_additional_mutating_calls(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_test_plans(
        "SourceProject",
        [
            TestPlan(
                id="tp-1",
                name="Release 1 Test Plan",
                suites=[TestSuite(id="ts-1", name="Smoke Tests")],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))

    migrate_test_plans(source, dest, "SourceProject", "DestProject", state)
    calls_after_first_run = len(dest.mutation_log)

    section = migrate_test_plans(source, dest, "SourceProject", "DestProject", state)

    assert len(dest.mutation_log) == calls_after_first_run
    assert section.items == ["Release 1 Test Plan"]


def test_migrate_test_plans_recreates_plan_deleted_from_destination(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=False)
    source.seed_test_plans(
        "SourceProject",
        [
            TestPlan(
                id="tp-1",
                name="Release 1 Test Plan",
                suites=[TestSuite(id="ts-1", name="Smoke Tests")],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))

    migrate_test_plans(source, dest, "SourceProject", "DestProject", state)
    dest._test_plans["DestProject"] = []

    section = migrate_test_plans(source, dest, "SourceProject", "DestProject", state)

    assert len(dest.list_test_plans("DestProject")) == 1
    assert section.items == ["Release 1 Test Plan"]


def test_migrate_test_plans_dry_run_reports_without_mutating(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    dest = InMemoryFakeAdoClient(dry_run=True)
    source.seed_test_plans(
        "SourceProject",
        [
            TestPlan(
                id="tp-1",
                name="Release 1 Test Plan",
                suites=[TestSuite(id="ts-1", name="Smoke Tests")],
            )
        ],
    )
    state = StateStore(str(tmp_path / "state.json"))

    section = migrate_test_plans(source, dest, "SourceProject", "DestProject", state)

    assert section.items == ["Release 1 Test Plan"]
    assert dest.list_test_plans("DestProject") == []
    assert state.is_complete("test_plans", source_id="tp-1") is False
