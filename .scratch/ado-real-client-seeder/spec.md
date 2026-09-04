Status: ready-for-agent

# Real Azure DevOps Client + Test-Data Seeder

## Problem Statement

The Azure DevOps migration framework built previously has only ever been exercised against in-memory fakes — no ticket in that effort ever built a real Azure DevOps API client, so the tool cannot currently talk to an actual Azure DevOps organization. There's also no way to generate realistic test data (projects, work items with history, repos with commits) in a real org, which means the migration tool's most complex logic — work item revision replay and git repository mirroring — has never been validated against the real API at all.

## Solution

Build `RealAdoClient` and `RealGitTransport` — real implementations of the existing `AdoClient`/`GitTransport` interfaces already used throughout the migration framework — covering read and write support for the three artifact types where real-org validation matters most: area/iteration paths, git repositories, and work items (including revision replay, attachments, and links). Because these implement the same interfaces the fakes already satisfy, no migrator code changes.

Alongside this, build a standalone `seed-ado` CLI command that uses `RealAdoClient`/`RealGitTransport` in write-only mode to populate a freshly created Azure DevOps project with realistic test data: a small area/iteration path tree, a couple of repos with real git commit history, and a handful of work items with revisions, cross-references, and an attachment. On success it writes a ready-to-use `migrate` config stub pointing at the new project, so seeding and then test-migrating a real org becomes a two-command workflow.

## User Stories

1. As a developer, I want a `RealAdoClient` that implements the same interface as the existing fake `AdoClient`, so `migrate` can run against a real org without any migrator code changing.
2. As a developer, I want `RealGitTransport` to perform actual `git clone --mirror` / `git push --mirror` operations, so real repository migrations can be validated end-to-end.
3. As a developer, I want `RealAdoClient` to support reading and creating area paths against a real org, so the area-path migrator works unmodified against real data.
4. As a developer, I want `RealAdoClient` to support reading and creating iteration paths (including start/end dates) against a real org, so the iteration-path migrator works unmodified against real data.
5. As a developer, I want `RealAdoClient` to support listing and creating repositories against a real org, so the repo migrator can create real destination repos.
6. As a developer, I want `RealAdoClient` to support creating a work item and then replaying every subsequent revision as a real update against a real org, so work item history replay is validated against the real API's actual revision semantics.
7. As a developer, I want `RealAdoClient` to support adding real attachment content to a work item, so attachment migration is validated end-to-end.
8. As a developer, I want `RealAdoClient` to support reading and updating work item links against a real org, so cross-reference link rewriting is validated end-to-end.
9. As a developer, I want `RealAdoClient`'s mutating calls to raise the existing `TransientError` on rate-limiting or transient HTTP failures, so the already-built retry-with-backoff in `DryRunGuard` applies automatically with no new retry logic.
10. As a developer, I want `RealAdoClient` authenticated via a PAT resolved the same way the rest of the tool resolves PATs (environment variable referenced by name), so credential handling stays consistent across the codebase.
11. As a test-data operator, I want a `seed-ado --org <url> --pat-env <VAR> --project-prefix <name>` command, so I can populate a real org with test data in one step.
12. As a test-data operator, I want the seeder to create a fresh Azure DevOps project on every run (using the asynchronous Create Project operation, polled until ready), so each run starts from a clean project without needing any reset or cleanup logic.
13. As a test-data operator, I want the seeder to create a small area/iteration path tree that includes at least one nested path, so hierarchy-ordering logic in the migrator gets exercised.
14. As a test-data operator, I want the seeder to create a couple of repositories, each with a handful of real git commits, so repo mirroring is exercised against real git history rather than an empty repo.
15. As a test-data operator, I want the seeder to create a configurable number of work items (default around 10) with a few revisions each, so revision replay is exercised at realistic (if small) scale.
16. As a test-data operator, I want some seeded work items to link to each other and to reference a pull request in a seeded repo, so cross-reference link rewriting has something real to resolve.
17. As a test-data operator, I want at least one seeded work item to carry a file attachment, so attachment migration has something real to move.
18. As a test-data operator, I want the logic that decides *what* test data to create to be a pure function of a count, independent of `RealAdoClient` itself, so it can be unit tested without touching a real org.
19. As a test-data operator, I want the seeder, after a successful run, to write a `migrate`-compatible `seeded-config.yaml` with the `source` section filled in (organization, the new project, PAT env var name) and the `destination` section left as an unmistakable placeholder, so running a real test migration afterward requires editing only the destination.
20. As a test-data operator, I want clear console progress output while seeding runs, consistent with the logging conventions `migrate` already uses.
21. As a test-data operator, I want a clear, specific error if project creation fails or times out (bad org/PAT, name collision, org quota), rather than a silent hang or a low-level stack trace.
22. As a developer, I want it explicitly documented that `RealAdoClient`, `RealGitTransport`, and the project-creation polling logic are deliberately excluded from the automated test suite, so a future contributor sees this as an intentional, reasoned exception rather than a coverage gap to "fix."

## Implementation Decisions

- This is a new, separate effort from the completed `ado-migration-framework` spec (that one's 15 tickets are all done) — own feature slug, own tickets, in this same local-markdown tracker.
- `RealAdoClient(AdoClient)` and `RealGitTransport(GitTransport)`: real implementations added alongside the existing fakes, satisfying the same interfaces migrator code already depends on. Scope is limited to the three core artifact types — area paths, iteration paths, repos, work items (create, revision replay, attachments, links) — for both read and write. The other nine artifact types (service connections, pipelines, queries, test plans, security groups, wikis, report-only detection) remain fake-only; extending real-client coverage to them is explicitly future work, not part of this spec.
- Authentication: PAT-based, using either HTTP Basic auth (empty username, PAT as password) or the `azure-devops` SDK's `BasicAuthentication` credential — consistent with the original project's "SDK where it covers, REST fallback otherwise" decision.
- Transient-failure mapping: `RealAdoClient`/`RealGitTransport` translate rate-limiting responses, 5xx responses, and network/git-command timeouts into the existing `TransientError`, so retry-with-backoff Just Works via the already-built `DryRunGuard._mutate` — no new retry code needed anywhere.
- Project creation uses the Azure DevOps Core API's asynchronous Create Project operation; the client polls the operation until it completes or times out, surfacing a specific error either way.
- `seed-ado` CLI takes plain flags (`--org`, `--pat-env`, `--project-prefix`) rather than a YAML config — a seeder invocation only has three inputs, and a config file would be pure ceremony.
- Seed-data generation is a standalone, pure module: given a work-item count, it produces the data structures to create (area/iteration path tree, per-repo commit plans, work item revision/link/attachment specs) without touching `RealAdoClient` at all. Guarantees baked into the generated plan: at least one nested area/iteration path, two repos with 3-5 commits each, at least one work-item-to-work-item link, at least one link referencing a PR in a seeded repo, and at least one attachment.
- On success, `seed-ado` writes `seeded-config.yaml`: a valid `migrate` config with `source` fully populated (organization URL, the newly created project name, the PAT env var name passed in) and `destination` fields set to an obvious placeholder value (e.g. `CHANGE_ME`) with an inline comment telling the operator to fill it in.
- `seed-ado` logs progress via the same `logging` module conventions already used by `migrate`'s orchestrator.

## Testing Decisions

- The seed-data generation logic is tested as pure functions/data: given a work-item count, assert on the shape of the returned plan (hierarchy nesting present, commit counts per repo, at least one cross-item link, at least one PR-reference link, at least one attachment) — no network access and no `RealAdoClient` involved.
- `seed-ado`'s CLI argument parsing and the `seeded-config.yaml` content generation are tested the same way `migrate`'s `parse_args` and config handling already are: as pure functions given inputs, asserting on outputs.
- `RealAdoClient`, `RealGitTransport`, and the project-creation polling loop are explicitly excluded from the automated test suite. No mocking of the HTTP/SDK/git-subprocess layer is used as a substitute. This is a deliberate, documented exception to this codebase's established "test only against fakes, never touch a real org" rule — not an oversight. Verification of this code is manual: actually running `seed-ado` and then `migrate` against a real Azure DevOps test organization.
- Every other part of the existing codebase continues under its established TDD discipline (red → green against fakes) unchanged; this spec does not touch or retest it.

## Out of Scope

- Extending `RealAdoClient`/`RealGitTransport` to the other nine artifact types (service connections, pipelines, queries, test plans, security groups, wikis, and report-only detection) — a natural future follow-up, not this spec.
- Cleanup or deletion of seeded projects (a `--cleanup` flag was discussed and explicitly deferred during design).
- Any automated (mocked or otherwise) testing of the real API/git-calling code itself.
- Load or performance testing — seeded data volumes are deliberately small, chosen to exercise migration *logic* (hierarchy, revision replay, link resolution), not to stress-test scale.
- CI integration for running the seeder or a real-org migration test — this remains a manual, local-developer workflow.

## Further Notes

- This spec exists because of a gap discovered while building ticket 14 of the `ado-migration-framework` spec: no ticket in that original 15-ticket plan ever built a real Azure DevOps API client, only fakes. This spec closes that gap for the three artifact types where real-org validation matters most (revision replay and git mirroring are the two things that genuinely cannot be meaningfully validated any other way), rather than for all twelve at once.
- Once this is built and manually verified against a real org, the natural next step — not part of this spec — is extending real-client coverage to the remaining nine artifact types, most likely following the same ticket-by-ticket pattern used for the original migration framework.
