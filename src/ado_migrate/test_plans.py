from ado_migrate.client import AdoClient, TestSuite
from ado_migrate.report import ReportSection
from ado_migrate.state import StateStore

ARTIFACT_TYPE = "test_plans"


def migrate_test_plans(
    source_client: AdoClient,
    dest_client: AdoClient,
    source_project: str,
    dest_project: str,
    state: StateStore,
) -> ReportSection:
    items = []

    for plan in source_client.list_test_plans(source_project):
        if not state.is_complete(ARTIFACT_TYPE, source_id=plan.id):
            destination_plan = dest_client.create_test_plan(dest_project, plan.name)
            destination_plan_id = (
                destination_plan.id if destination_plan is not None else None
            )

            suite_id_map: dict[str, str] = {}
            for suite in _parent_first_suites(plan.suites):
                parent_destination_id = (
                    suite_id_map.get(suite.parent_suite_id)
                    if suite.parent_suite_id
                    else None
                )
                resolved_test_case_ids = [
                    state.get_destination_id("work_items", source_id=tc_id) or tc_id
                    for tc_id in suite.test_case_ids
                ]

                destination_suite = dest_client.create_test_suite(
                    dest_project,
                    destination_plan_id,
                    suite.name,
                    parent_destination_id,
                    resolved_test_case_ids,
                    suite.configuration_names,
                )
                if destination_suite is not None:
                    suite_id_map[suite.id] = destination_suite.id

            if not dest_client.dry_run:
                state.mark_complete(
                    ARTIFACT_TYPE, source_id=plan.id, destination_id=destination_plan_id
                )

        items.append(plan.name)

    return ReportSection(title="Test Plans", items=items)


def _parent_first_suites(suites: list[TestSuite]) -> list[TestSuite]:
    resolved: set[str] = set()
    ordered: list[TestSuite] = []
    remaining = list(suites)

    while remaining:
        progressed = False
        next_remaining = []
        for suite in remaining:
            if suite.parent_suite_id is None or suite.parent_suite_id in resolved:
                ordered.append(suite)
                resolved.add(suite.id)
                progressed = True
            else:
                next_remaining.append(suite)

        if not progressed:
            ordered.extend(next_remaining)
            break
        remaining = next_remaining

    return ordered
