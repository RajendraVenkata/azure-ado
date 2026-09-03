# 15: End-to-end idempotency & report verification

**What to build:** A full-scope verification pass proving the assembled system's core promises hold together: a dry run followed by a real run followed by a repeated real run, covering every artifact type in one pass against the fake backend, with a complete and accurate HTML report throughout.

**Blocked by:** 14: Full orchestration

**Status:** ready-for-agent

- [ ] A full dry run against a fake backend seeded with every artifact type produces an HTML report accurately describing every item that would be migrated, skipped, or report-only
- [ ] A full real run against the same seeded fake backend migrates every in-scope artifact type and produces a state file with a complete ID-mapping table
- [ ] Re-running the same real run a second time makes no additional mutating calls and produces identical end state (no duplicates anywhere)
- [ ] The post-run HTML report accurately reflects final state: what was migrated, what was skipped as report-only, and what external references were retained
- [ ] This is the only ticket that exercises the assembled system end-to-end; all prior tickets remain independently tested against the fake backend
