# 07: Cross-reference link rewriting

**What to build:** A second pass that rewrites work item links and PR links to point at their migrated destination counterparts, while preserving (and reporting) links that point at something intentionally out of scope.

**Blocked by:** 04: Git repository migration, 06: Work item migration

**Status:** ready-for-agent

- [ ] After work items and repos are migrated, links between two migrated work items are rewritten to reference the destination work item IDs, using the ID-mapping table in state
- [ ] PR references within migrated work items are rewritten to reference the destination repo/PR, using the ID-mapping table
- [ ] A link whose target is out of migration scope (a different, non-migrated project, or a report-only artifact type such as a classic release pipeline or dashboard) is left pointing at the source org rather than dropped or broken
- [ ] Every such preserved external link is itemized in the HTML report under "external references retained"
- [ ] Re-running link rewriting on already-rewritten items is a no-op (idempotent)
- [ ] Covered by tests against the fake `AdoClient` — no real org involved
