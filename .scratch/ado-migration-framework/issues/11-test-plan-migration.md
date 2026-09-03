# 11: Test plan / suite / case migration

**What to build:** Migrating the test plan/suite hierarchy and test case structure to the destination (structure only — no run history/results).

**Blocked by:** 06: Work item migration

**Status:** ready-for-agent

- [ ] Source test plans and their suite hierarchy are read and recreated on the destination
- [ ] Test cases (migrated as work items via ticket 06) are correctly linked into their destination test suites
- [ ] Test configurations are migrated where referenced by a plan/suite
- [ ] No test run history or execution results are migrated or reported (explicitly out of scope)
- [ ] Migrated test plans/suites are tracked in state; re-running skips ones already migrated
- [ ] A dry run lists the test plans/suites that will be migrated in the HTML report
- [ ] Covered by tests against the fake `AdoClient`
