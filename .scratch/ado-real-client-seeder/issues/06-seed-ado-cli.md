# 06: seed-ado CLI — project creation, full seeding, config stub

**What to build:** The `seed-ado` command: creates a fresh Azure DevOps project, feeds the generated seed plan through the real clients to actually populate it, and writes a ready-to-use `migrate` config stub — turning "seed a real org" and "test-migrate it" into a two-command workflow.

**Blocked by:** 01: RealAdoClient — area & iteration paths, 02: RealAdoClient — repos + RealGitTransport, 03: RealAdoClient — work items, 04: RealAdoClient — work item links, 05: Seed-data generation

**Status:** ready-for-agent

- [x] `seed-ado --org <url> --pat-env <VAR> --project-prefix <name>` is a working CLI entrypoint (plain flags, no YAML config) — also accepts `--work-item-count`
- [x] Creates a fresh Azure DevOps project via the asynchronous Create Project API, polling until the operation completes; a failure or timeout produces a clear, specific error rather than a silent hang or a raw stack trace (process template is looked up dynamically per org, preferring Agile/Scrum/CMMI/Basic in that order, since inherited-process template GUIDs are org-specific, not global)
- [x] Generates the seed plan (ticket 05) and creates every planned area path, iteration path, repo (with real commits pushed), and work item (with revisions, links, and attachment) in the new project via the real clients from tickets 01–04
- [x] Logs progress during the run (what's being created, done), consistent with `migrate`'s existing logging conventions
- [x] On success, writes `seeded-config.yaml`: a valid `migrate` config with `source` fully populated (organization URL, new project name, PAT env var name) and `destination` fields set to an unmistakable placeholder value with an inline comment
- [x] CLI argument parsing and `seeded-config.yaml` content generation are covered by unit tests (2 tests, pure functions given inputs), matching how `migrate`'s own CLI parsing is tested
- [ ] **Not yet done:** manual verification of a full run against a real org. What *was* verified in this session, beyond SDK introspection: the local commit/push sequence (`_push_seeded_commits`) was run end-to-end against a real local bare git repo (temp dir "remote", not ADO) — confirmed it creates the working tree files, commits them in order with the right messages, and pushes correctly; `_resolve_link` was exercised directly and correctly resolves both work-item and pull-request plan-local placeholders to their (mocked) destination ids. The Azure DevOps-specific calls (project creation, `queue_create_project`/`get_operation` polling, process template lookup) are implemented per SDK introspection only, not run against a real org.
- [x] The end-to-end run (project creation through to a populated project and a written config) is explicitly excluded from the automated test suite and is verified manually against a real org, per the spec's testing decision
