# 06: Work item migration (creation, full revision replay, attachments)

**What to build:** Migrating work items to the destination with their full revision history replayed (not a single snapshot), attachments included, correctly assigned via identity mapping, and correctly placed via migrated area/iteration paths.

**Blocked by:** 01: Core engine scaffolding, 02: Identity mapping, 03: Area & iteration path migration

**Status:** ready-for-agent

- [ ] Each source work item is created on the destination, then every historical revision is replayed in order so the destination's revision history mirrors the source's field-by-field change history
- [ ] Assigned To (and other identity-bearing fields) are resolved through the identity mapping from ticket 02, including its fallback behavior for unmapped users
- [ ] Work items are placed under the destination area/iteration paths created in ticket 03, corresponding to their source paths
- [ ] File attachments on a work item are migrated as binary content alongside the work item
- [ ] The source-ID → destination-ID mapping table in state is populated for every migrated work item
- [ ] Migrated work items are tracked in state; re-running skips work items already fully migrated
- [ ] A dry run lists the work items that will be migrated in the HTML report
- [ ] Covered by tests against the fake `AdoClient` — no real org involved
