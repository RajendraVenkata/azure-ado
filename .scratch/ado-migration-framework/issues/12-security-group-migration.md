# 12: Security groups & permissions (best-effort)

**What to build:** Best-effort recreation of custom security groups and their memberships on the destination, using the identity mapping, with anything that can't be resolved skipped and reported rather than guessed at.

**Blocked by:** 02: Identity mapping

**Status:** ready-for-agent

- [ ] Source custom security groups are read and recreated on the destination
- [ ] Group memberships are recreated using resolved destination identities from the identity mapping (ticket 02)
- [ ] A membership or permission override with no resolvable destination identity is skipped (not force-applied or guessed) and recorded for reporting
- [ ] Migrated groups/memberships are tracked in state; re-running skips ones already migrated
- [ ] A dry run lists the groups/memberships that will be migrated, and those that will be skipped with reasons, in the HTML report
- [ ] Covered by tests against the fake `AdoClient`
