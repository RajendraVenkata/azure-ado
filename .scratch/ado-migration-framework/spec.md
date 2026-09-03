Status: ready-for-agent

# Azure DevOps Org-to-Org Migration Framework

## Problem Statement

Teams that need to move an Azure DevOps project from one organization to another (e.g. splitting a business unit, changing tenants, consolidating orgs) currently have no reliable way to do it. Manually recreating repos, work items, boards configuration, pipelines, and everything else that makes up a project is slow, error-prone, and loses history (git history, work item revision history) unless done very carefully. There's no safe way to "try it first" before committing to a real cutover, and if a migration run fails partway through, there's no way to know what's already been moved versus what still needs doing — re-running risks creating duplicates.

## Solution

A Python CLI framework, driven by a per-project-pair YAML config (source org/project, destination org/project, PAT token references), that migrates a project's content and metadata from a source Azure DevOps organization to a destination organization. It supports a **dry-run mode** that produces an HTML report describing exactly what would happen, without writing anything to the destination. Real runs record progress in a local state file (per-item completion status plus a source-ID → destination-ID mapping table), making re-execution **idempotent**: a failed or interrupted run can simply be re-run, and already-completed work is skipped rather than duplicated. A `--only <types>` flag also allows deliberately re-running a subset of artifact types (e.g. to re-validate work items after fixing a mapping issue) independent of automatic resume behavior.

Migration covers Git repos and wikis (full history, via git mirroring), work items (full revision-by-revision history replay, including attachments), area/iteration paths, YAML build pipelines, service connections, test plans/suites/cases, queries, and security groups/permissions (best-effort, driven by a user-supplied identity mapping between source and destination user accounts). Artifact types that are org-level, high-risk to automate, or a fundamentally different kind of problem (classic release pipelines, dashboards, artifact feeds/packages, marketplace extensions, and all historical execution data — build run history and test run results) are deliberately **not** migrated automatically; they're itemized in the HTML report for manual follow-up instead.

## User Stories

1. As a migration operator, I want to define a source project, destination project, and their respective PAT tokens in a single YAML config file, so that I have one place that describes a migration.
2. As a migration operator, I want the config file to reference PAT tokens by environment variable name rather than embedding the token value, so that secrets never end up committed to version control or shared config files.
3. As a migration operator, I want to run the tool in dry-run mode before ever touching the destination org, so that I can validate what will happen without risk.
4. As a migration operator, I want the dry-run output to be a readable HTML report, so that I can review and share the migration plan with stakeholders who aren't going to read logs.
5. As a migration operator, I want the dry-run report to clearly separate "will be migrated," "will be skipped (already migrated)," and "will not be migrated — report only," so that I understand exactly what automation will and won't do.
6. As a migration operator, I want the HTML report to list every classic release pipeline, dashboard, artifact feed, and marketplace extension the source project uses, so that I have a manual-follow-up checklist for the things this tool intentionally doesn't automate.
7. As a migration operator, I want git repositories migrated with their full commit history intact, so that the destination repo is a faithful clone, not a fresh start.
8. As a migration operator, I want project wikis migrated the same way as regular repos, so that wiki history is preserved too.
9. As a migration operator, I want work items migrated with their full revision history replayed on the destination, so that "who changed what, when" is preserved, not just the current state.
10. As a migration operator, I want work item attachments (screenshots, logs, files) migrated along with the work item, so that I don't lose the most useful evidence attached to bugs and tasks.
11. As a migration operator, I want to supply an identity mapping file (source user → destination user), so that Assigned To, reviewers, and group memberships are correctly reassigned even when source and destination orgs are on different tenants.
12. As a migration operator, I want a defined fallback behavior when a source user has no destination mapping, so that migration doesn't silently mis-attribute or hard-fail on unmapped users.
13. As a migration operator, I want area paths and iteration paths recreated on the destination before work items are migrated, so that work items can be correctly placed without manual patching afterward.
14. As a migration operator, I want YAML build pipeline definitions migrated, so that CI keeps working after cutover without hand-rebuilding pipeline configuration.
15. As a migration operator, I want service connections recreated on the destination (as far as the API allows) before pipelines that reference them are migrated, so that pipeline definitions don't reference dangling connections.
16. As a migration operator, I want test plans, test suites, and test cases migrated (as structure, not execution history), so that QA doesn't have to manually rebuild test organization.
17. As a migration operator, I want shared queries migrated, with any area/iteration path values in the query rewritten to the destination paths, so that saved queries still return correct results after migration.
18. As a migration operator, I want custom security groups and their memberships recreated on the destination on a best-effort basis, using the identity mapping, so that access control doesn't have to be rebuilt entirely from scratch.
19. As a migration operator, I want any permission or group membership that can't be cleanly mapped (e.g. no destination identity match) to be skipped and reported rather than silently dropped or guessed at, so that I know exactly what needs manual attention.
20. As a migration operator, I want work item links, PR links, and other cross-references rewritten to point at the corresponding destination items after migration, so that navigating between migrated items works.
21. As a migration operator, I want links that point at something intentionally out of scope (a different, non-migrated project, a classic release pipeline, a dashboard) to be preserved as a working link back to the source org rather than silently dropped, so that the reference isn't lost even though it isn't rewritten.
22. As a migration operator, I want those preserved external links called out explicitly in the report, so I know they still point at the (eventually decommissioned) source org.
23. As a migration operator, I want a local state file that records, per artifact, whether it has been migrated and what its destination ID is, so that the tool has a durable record of progress.
24. As a migration operator, I want to re-run the tool after a crash or partial failure and have it pick up where it left off, so that I never end up with duplicate work items, repos, or pipelines from a retried run.
25. As a migration operator, I want to target a re-run at a specific artifact type (e.g. `--only workitems`) so that I can re-validate or retry one part of the migration without touching artifact types that already completed successfully.
26. As a migration operator, I want the tool to migrate artifact types in an order that respects their dependencies (e.g. area paths before work items, repos and service connections before pipelines), so that later steps don't fail due to missing prerequisites.
27. As a migration operator, I want transient API failures (rate limiting, network blips) to be retried automatically rather than aborting the whole run, so that a flaky connection doesn't force a full restart.
28. As a migration operator, I want a persistent failure on one item to be recorded and reported rather than silently skipped or crashing the entire run, so that one bad work item doesn't block migration of everything else.
29. As a migration operator, I want clear logging of what the tool is doing during a real run, so that I can monitor progress and diagnose issues as they happen.
30. As a migration operator, I want the config file format (YAML) to support comments, so that I can document why a project pair or setting is configured the way it is.
31. As a migration operator, I want the tool scoped to one source/destination project pair per config and per run, so that I can invoke it repeatedly (e.g. from a wrapper script or CI) for a full-org migration without the tool itself needing to understand "migrate everything in the org."
32. As a migration operator, I want the HTML report from a dry run to be diffable/comparable against a later dry run, so that I can confirm nothing unexpected changed on the source between validation and the real cutover.
33. As a developer extending this framework, I want all Azure DevOps API interaction to go through a single client abstraction (rather than scattered SDK/REST calls throughout the migrators), so that the system is testable without hitting a real org.
34. As a developer extending this framework, I want git content transfer isolated behind its own small interface, so that repo/wiki migration logic can be tested without invoking real git subprocesses.
35. As a migration operator, I want the state file's ID-mapping table to be usable as an audit trail after migration, so that I can answer "what did source item X become on the destination?" after the fact.

## Implementation Decisions

- **Scope, per artifact type:**
  - Fully migrated: Git repositories (full history), project wikis (full history — wikis are git-backed), work items (full revision-by-revision history replay + attachments), area paths, iteration paths, YAML build pipeline definitions, service connections, test plans/suites/cases (structure only), shared queries, security groups and memberships (best-effort).
  - Report-only (detected and listed in the HTML report, never written to the destination): classic release pipelines, dashboards and their widgets, Azure Artifacts feeds/packages, marketplace extensions in use by the source project.
  - Explicitly excluded from both migration and reporting depth: pipeline build run history, test run results/execution logs.
- **Run model:** one project pair per config/run. Full-org migrations are handled by invoking the tool once per project (external looping), not by the tool itself.
- **Config:** YAML file per project pair — source org/project, destination org/project, and PAT tokens referenced by environment variable name (never embedded as literal values in the file).
- **API access:** the `azure-devops` Python SDK is used wherever it covers the needed operation; raw Azure DevOps REST API calls are the fallback where the SDK doesn't cover something. All such calls are made through a single client abstraction (`AdoClient` or equivalent) rather than being scattered through migrator modules — this is also the primary test seam (see Testing Decisions).
- **Git/wiki content transfer:** uses git itself (`git clone --mirror` from source, `git push --mirror` to a destination repo created via the API), isolated behind its own transport interface, separate from the SDK/REST client. This applies identically to wikis, since Azure DevOps wikis are git-backed.
- **Work item history:** full revision replay — each historical revision is recreated in order on the destination so the destination work item's history trail matches the source, rather than a single snapshot with a "migrated from" note. Attachments are migrated as binary content alongside the work item.
- **Identity mapping:** a YAML lookup file mapping source user identity (e.g. email/UPN) to destination user identity, with a defined fallback behavior for source users with no mapping entry (e.g. assign to a placeholder/unmapped-owner rather than failing the item). This mapping drives reassignment of Assigned To, PR reviewers, and security group membership.
- **Permissions/security groups:** best-effort recreation of custom security groups and their memberships using the identity mapping above. Permission overrides or memberships that can't be resolved (no destination identity match, or otherwise unmappable) are skipped and itemized in the report rather than guessed at.
- **Cross-reference rewriting:** a two-pass approach — all items of a given type are created first, populating the ID-mapping table in state, then a second pass rewrites links/references using that table. References that point at something out-of-scope (another non-migrated project, a report-only artifact type) are left pointing at the source org and are separately itemized in the report as "external references retained," rather than being dropped.
- **State management:** a local state file per project-pair run recording, per migrated item, its completion status and its source-ID → destination-ID mapping. Re-running the tool checks this state before acting on each item, skipping already-completed work — this is what makes re-execution idempotent. Exact file format/schema is an implementation detail, not specified here.
- **CLI:** supports a full run (`migrate --config config.yaml [--dry-run]`) and a targeted run (`--only <types>` to restrict to specific artifact types), in addition to automatic resume-based skipping from state.
- **Migration ordering:** artifact types are migrated in dependency order (e.g. area/iteration paths and service connections before the artifact types that reference them; work items/repos created before cross-reference rewriting runs). Exact ordering is an implementation detail derived from the dependency relationships described above.
- **Error handling:** transient failures (rate limiting, network errors) are retried automatically; a persistent failure on a single item is recorded in state/report and does not abort the entire run. Exact retry policy (backoff strategy, retry counts) is an implementation detail.
- **Dry-run report:** an HTML report generated from a dry-run invocation, showing planned actions per artifact type, diffs against current destination state, and the report-only/skipped/external-link items described above.

## Testing Decisions

- Tests exercise real migration logic — ordering, ID-mapping, revision replay, dry-run diffing, state read/write — against a fake/in-memory implementation of the Azure DevOps client (`AdoClient`) and the git transport interface. No tests hit a real Azure DevOps organization, and no tests mock individual HTTP calls scattered through migrator code — the client/transport interfaces are the one seam.
- Good tests assert on externally observable behavior: contents of the state file after a run, contents of the generated HTML report, the resulting ID-mapping table, and the order operations occur in — not on "was internal method X called."
- Idempotency must be directly tested: running the full migration twice against the same fake backend produces no duplicate items and identical end state to running it once.
- Dry-run vs. real-run must be directly tested: dry-run against a fake backend results in zero mutating calls to the client/transport, only a report.
- No existing test suite or conventions exist in this (currently empty) repo; this framework establishes its own conventions, expected to use `pytest`.

## Out of Scope

- Classic release pipeline migration (definitions are report-only).
- Dashboard and widget migration (report-only).
- Artifact feed/package content migration (report-only).
- Marketplace extension installation on the destination org (report-only, detection only).
- Pipeline build run history and test run execution results/logs (excluded entirely, not even reported).
- Ongoing/repeated synchronization between source and destination after initial migration — this is a one-time migration tool with idempotent resume, not a continuous sync tool.
- Migrating multiple projects, or an entire organization, in a single invocation — achieved externally by invoking the tool once per project.
- Full-fidelity permission/ACL migration where destination identities can't be resolved — these are surfaced in the report for manual handling, not force-applied.

## Further Notes

- Several report-only carve-outs (classic release pipelines, dashboards, artifact feeds, extensions) exist because these are either org-level concepts that don't map to a single project migration, or because faithfully recreating them via API is disproportionately fragile/high-effort relative to the value of automating them — recreating them manually is comparatively cheap.
- Given the breadth of scope, a phased implementation is expected even though the spec covers the full artifact-type list: git repos + work items are the two artifact types containing irreplaceable data and the most complex identity/relationship problems, and are the natural first milestone; other artifact types build on the same client/state/report infrastructure once that foundation is proven.
- This spec assumes source and destination are genuinely different organizations (possibly different tenants), which is why identity mapping (rather than an assumed 1:1 email match) is part of the core design, not an edge case.
