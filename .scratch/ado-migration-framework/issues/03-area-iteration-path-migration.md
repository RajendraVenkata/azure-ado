# 03: Area & iteration path migration

**What to build:** Recreating the source project's area path and iteration path trees on the destination project, ahead of work items so they have somewhere correct to land.

**Blocked by:** 01: Core engine scaffolding

**Status:** ready-for-agent

- [ ] Source area path tree is read and recreated on the destination, preserving hierarchy
- [ ] Source iteration path tree (including start/end dates where present) is read and recreated on the destination, preserving hierarchy
- [ ] Paths already present on the destination (e.g. the project's default tree) are handled without creating duplicates or erroring
- [ ] Migrated paths are tracked in state; re-running skips paths already migrated
- [ ] A dry run lists the area/iteration paths that will be created in the HTML report
- [ ] Covered by tests against the fake `AdoClient` — no real org involved
