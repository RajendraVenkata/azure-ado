# 14: Full orchestration — dependency ordering, retry/error handling, `--only`

**What to build:** A single orchestrator that runs every migrator from tickets 03–13 in correct dependency order, retries transient failures automatically, continues past a persistent per-item failure rather than aborting the whole run, and exposes a `--only <types>` CLI flag for targeted runs.

**Blocked by:** 03: Area & iteration path migration, 04: Git repository migration, 05: Wiki migration, 06: Work item migration, 07: Cross-reference link rewriting, 08: Service connection migration, 09: YAML build pipeline migration, 10: Shared query migration, 11: Test plan / suite / case migration, 12: Security groups & permissions, 13: Report-only artifact detection

**Status:** ready-for-agent

- [ ] A full run (`migrate --config config.yaml`) executes all migrators in an order that respects their dependencies (e.g. area/iteration paths and service connections before the artifact types that reference them; cross-reference rewriting after the items it rewrites)
- [ ] `--only <types>` restricts a run to the specified artifact type(s), skipping the rest, while still respecting state-based resume
- [ ] Transient failures (rate limiting, network errors) from `AdoClient`/`GitTransport` are retried automatically with backoff before being treated as a failure
- [ ] A persistent failure on a single item is recorded in state and reported, and the run continues migrating other items/types rather than aborting entirely
- [ ] Logging during a real run clearly communicates current progress (artifact type, item, outcome)
- [ ] Covered by tests against the fake `AdoClient`/`GitTransport`, including a scenario where one item fails persistently and the run still completes the rest
