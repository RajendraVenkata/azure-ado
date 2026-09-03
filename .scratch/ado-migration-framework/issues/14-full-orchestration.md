# 14: Full orchestration — dependency ordering, retry/error handling, `--only`

**What to build:** A single orchestrator that runs every migrator from tickets 03–13 in correct dependency order, retries transient failures automatically, continues past a persistent per-item failure rather than aborting the whole run, and exposes a `--only <types>` CLI flag for targeted runs.

**Blocked by:** 03: Area & iteration path migration, 04: Git repository migration, 05: Wiki migration, 06: Work item migration, 07: Cross-reference link rewriting, 08: Service connection migration, 09: YAML build pipeline migration, 10: Shared query migration, 11: Test plan / suite / case migration, 12: Security groups & permissions, 13: Report-only artifact detection

**Status:** ready-for-agent

- [x] A full run (`migrate --config config.yaml`) executes all migrators in an order that respects their dependencies (e.g. area/iteration paths and service connections before the artifact types that reference them; cross-reference rewriting after the items it rewrites)
- [x] `--only <types>` restricts a run to the specified artifact type(s), skipping the rest, while still respecting state-based resume
- [x] Transient failures (rate limiting, network errors) from `AdoClient`/`GitTransport` are retried automatically with backoff before being treated as a failure
- [x] A persistent failure is recorded in state and reported, and the run continues migrating other artifact types rather than aborting entirely (scoped to per-artifact-type resilience, not per-item within a type — see comment below)
- [x] Logging during a real run clearly communicates current progress (artifact type, item, outcome)
- [x] Covered by tests against the fake `AdoClient`/`GitTransport`, including a scenario where one item fails persistently and the run still completes the rest

**Implementation note:** persistent-failure resilience is per-artifact-type, not per-item within a type (confirmed with the user during implementation) — implemented entirely in the orchestrator + the shared `DryRunGuard`, with no changes to the 9 already-built migrator files. A failure partway through one artifact type stops the rest of that type's items, but every other type still runs.

**Gap discovered during this ticket:** no ticket ever built a real SDK/REST-backed `AdoClient`/`GitTransport` — every artifact-type method (tickets 03–13) was only ever added to the in-memory fakes. `main()`'s CLI entrypoint is now fully wired end-to-end, but constructing bare `AdoClient`/`GitTransport` instances for a real run means every step fails immediately (verified: `main()` against a real config produces `AttributeError` on every artifact type, though the orchestrator's resilience means it still exits 0 rather than crashing). This tool cannot yet talk to a real Azure DevOps organization. Implementing the real client was never one of the 15 scoped tickets; it needs its own follow-up ticket.
