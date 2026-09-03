# 10: Shared query migration

**What to build:** Migrating shared work item queries to the destination, with area/iteration path values in the query rewritten to the destination paths so results stay correct.

**Blocked by:** 03: Area & iteration path migration

**Status:** ready-for-agent

- [ ] Source shared queries (WIQL definitions and folder structure) are read and recreated on the destination
- [ ] Any area/iteration path value embedded in a query clause is rewritten to the corresponding destination path
- [ ] Migrated queries are tracked in state; re-running skips queries already migrated
- [ ] A dry run lists the queries that will be migrated in the HTML report
- [ ] Covered by tests against the fake `AdoClient`
