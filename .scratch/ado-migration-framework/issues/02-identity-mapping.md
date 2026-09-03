# 02: Identity mapping

**What to build:** Loading and resolving a source-user → destination-user identity mapping, so later migrators (work items, security groups) can correctly reassign ownership across orgs/tenants instead of assuming emails match 1:1.

**Blocked by:** 01: Core engine scaffolding

**Status:** ready-for-agent

- [ ] A YAML identity-mapping file format is defined and loaded at startup, mapping source user identity (email/UPN) to destination user identity
- [ ] Given a source identity present in the mapping, resolution returns the correct destination identity
- [ ] Given a source identity absent from the mapping, resolution applies the defined fallback (e.g. a placeholder/unmapped-owner) rather than raising an unhandled error or silently dropping the assignment
- [ ] Unmapped identities encountered during a run are recorded (for later surfacing in the report by consuming tickets)
- [ ] Covered by tests against sample mapping data — no real Azure DevOps org involved
