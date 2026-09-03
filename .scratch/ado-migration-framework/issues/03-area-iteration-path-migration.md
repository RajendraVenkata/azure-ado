# 03: Area & iteration path migration

**What to build:** Recreating the source project's area path and iteration path trees on the destination project, ahead of work items so they have somewhere correct to land.

**Blocked by:** 01: Core engine scaffolding

**Status:** ready-for-agent

- [x] Source area path tree is read and recreated on the destination, preserving hierarchy
- [x] Source iteration path tree (including start/end dates where present) is read and recreated on the destination, preserving hierarchy
- [x] Paths already present on the destination (e.g. the project's default tree) are handled without creating duplicates or erroring
- [x] Migrated paths are tracked in state; re-running skips paths already migrated
- [x] A dry run lists the area/iteration paths that will be created in the HTML report
- [x] Covered by tests against the fake `AdoClient` — no real org involved
