# Azure DevOps Migration Framework — Spec

Status: ready-for-agent

## Problem Statement

Teams that need to move an Azure DevOps project (or several) from one organization to another currently have no reliable, repeatable way to do it. Manually re-creating work items, area/iteration structure, and git repositories is slow, error-prone, loses authorship and history metadata, and can't safely be re-run after a partial failure without risking duplicates. There's also no way to preview what a migration will actually do before committing to it.

## Solution

A Python CLI framework (`ado-migrate`) that reads a YAML config describing a source org, a destination org, and one or more project mappings between them, and migrates work items (fields, links, attachments, comments), area/iteration paths (with dates), and git repositories (code + branches) from source to destination. A `plan` command performs a dry run — validating config, connectivity, and destination permissions — and produces an HTML report of exactly what will happen. An `apply` command executes the migration, tracking per-item progress in a local SQLite state store so reruns are idempotent: already-migrated items are never re-touched, and only items left `pending` or `failed` from a prior run are retried. A `status` command reports current progress from that state store.

## User Stories

1. As a migration operator, I want to specify source and destination organizations with PAT tokens referenced via environment variable names in a config file, so that credentials never appear in plaintext in a file I might commit or share.
2. As a migration operator, I want to load PAT values from a local `.env` file during development, so that I don't have to export environment variables manually every time I test.
3. As a migration operator, I want the tool to reject a config where a PAT-looking literal token is pasted directly into the YAML, so that I don't accidentally commit a secret.
4. As a migration operator, I want to list multiple source-project → destination-project mappings in a single config file, so that I can migrate several projects within the same org pair in one run.
5. As a migration operator, I want to run `ado-migrate plan --config config.yaml` and get an HTML report before anything is written to the destination, so that I can review exactly what will happen and catch problems early.
6. As a migration operator, I want the dry-run report to show a summary count of planned actions per entity type (work items, paths, repos), so that I can quickly gauge the size and shape of the migration.
7. As a migration operator, I want the dry-run report to include a full per-item table (ID, title/name, planned action, flags) for every work item, path, and repo, so that I can inspect individual items before committing to `apply`.
8. As a migration operator, I want `plan` to validate that the destination project already exists, so that I don't attempt a migration into a project that hasn't been provisioned yet.
9. As a migration operator, I want `plan` to validate that the destination PAT has the "Bypass rules on work item updates" permission, so that I discover permission problems before `apply` fails partway through.
10. As a migration operator, I want `plan` to validate that the destination project's process template has matching work item types and fields for everything the source will send, so that I can fix template gaps before running `apply`.
11. As a migration operator, I want unmapped source identities (users with no entry in `identity_map`) flagged in the dry-run report, so that I can add the missing mapping before `apply` creates work items with a blank or wrong assignee.
12. As a migration operator, I want work item links pointing to items outside the migration's scope flagged in the report, so that I understand which relationships won't be recreated as live links in the destination.
13. As a migration operator, I want to run `ado-migrate apply --config config.yaml` to actually perform the migration, so that I can move the configured projects from source to destination.
14. As a migration operator, I want each migrated work item's original field state preserved as closely as possible (including `CreatedBy`, `CreatedDate`, `ChangedDate`, and `State` via `bypassRules`), so that the destination history looks authentic rather than showing everything created today by a migration service account.
15. As a migration operator, I want each migrated work item's attachments carried over, so that no supporting files are lost in the move.
16. As a migration operator, I want each migrated work item's full comment/discussion thread carried over, so that context and conversation history aren't lost even though full field-level revision history isn't replayed.
17. As a migration operator, I want each migrated work item to include a comment linking back to its source item's URL and ID, so that anyone auditing the destination can trace an item back to where it came from.
18. As a migration operator, I want area paths and iteration paths (including iteration start/finish dates) recreated in the destination project before work items are migrated, so that work items referencing those paths can be created successfully.
19. As a migration operator, I want git repositories in a source project mirrored (code + all branches, no PR history) to the destination project by default, so that I don't have to enumerate every repo by hand.
20. As a migration operator, I want to explicitly include or exclude specific repos per project in config, so that I can skip a repo I don't want migrated (e.g. an archived/test repo) without disabling automatic discovery for the rest.
21. As a migration operator, I want disabled repos skipped automatically, so that dead repos don't clutter the migration.
22. As a migration operator, I want a rerun of `apply` to skip anything already marked `migrated` in the local state store, so that I can safely re-run the tool after a partial failure without creating duplicate work items or re-pushing repos that already succeeded.
23. As a migration operator, I want a failed item during `apply` to be logged and marked `failed` in state, with the rest of the run continuing, so that one bad work item doesn't block migrating everything else.
24. As a migration operator, I want an opt-in `--fail-fast` flag on `apply`, so that I can choose abort-on-first-error behavior when I'd rather stop immediately and investigate.
25. As a migration operator, I want to run `ado-migrate status --config config.yaml` at any time, so that I can see how many items of each type are `pending`, `migrated`, or `failed` without re-running a full plan or apply.
26. As a migration operator, I want the tool installed as a standard Python package with a single `ado-migrate` console-script entry point, so that I can install it with `pip install -e .` and run it from anywhere without remembering module paths.
27. As a migration operator, I want the documentation to clearly state which Azure DevOps entity types are out of scope for this version (pipelines, wikis, test plans, service connections, permissions, Development links), so that I don't assume the tool does more than it does.
28. As a migration operator, I want the tool to work only against Azure DevOps Services (cloud), so that I have accurate expectations if I'm actually running an on-prem Server/TFS instance (unsupported).
29. As a migration operator migrating a project a second time by mistake, I want already-migrated git repos left untouched by `apply` even though a git mirror push is naturally incremental, so that repo behavior stays consistent with the one-time semantics used for every other entity type.
30. As a developer maintaining this framework, I want the ADO REST API boundary mocked with recorded fixtures in tests (no live sandbox org required), so that the test suite runs fast and deterministically in CI.
31. As a developer maintaining this framework, I want git-repo migration tested against real local `file://` temp repos rather than mocked subprocess calls, so that git plumbing bugs are caught by tests that exercise the real `git` binary.

## Implementation Decisions

- **CLI layer**: a `click`-based command group with three subcommands — `plan`, `apply`, `status` — each taking `--config <path>`; `apply` additionally takes an opt-in `--fail-fast` flag. Packaged as an installable Python project (minimum Python 3.11) with a single `ado-migrate` console-script entry point.
- **Config loader/validator**: parses the YAML config into a typed model — `source` (organization URL, `pat_env`), `destination` (organization URL, `pat_env`), `projects` (list of `{source_project, destination_project, repos: {include, exclude}}`), `identity_map` (source-identity → destination-identity mapping). Loads a local `.env` (via `python-dotenv`) before resolving PAT env vars. Rejects any config value that looks like a literal PAT rather than an environment variable name.
- **ADO client layer**: thin wrappers around the official `azure-devops` SDK, one connection each for source and destination org, built from org URL + resolved PAT. Raw `requests` calls used only for endpoints the SDK doesn't expose, sharing the same auth/base-URL setup as the SDK connection.
- **Domain services**, one per entity type, each exposing a `plan_<entity>()` step (read-only; returns planned actions/flags) and an `apply_<entity>()` step (performs writes, consults and updates the state store):
  - **Path service** — area paths, iteration paths (with start/finish dates). Runs first, since work items reference paths.
  - **Work item service** — two-pass creation: pass one creates every in-scope work item (with `bypassRules` to preserve `CreatedBy`/`CreatedDate`/`ChangedDate`/`State`, plus fields, attachments, and the copied comment thread) without cross-item links, since destination IDs aren't known until creation; pass two applies work item links using the source→destination ID mapping recorded in state during pass one. Appends the traceability comment (source URL + ID) after the copied comment thread. Links whose target wasn't migrated in this run are flagged rather than recreated.
  - **Repo service** — enumerates non-disabled repos per project (or the configured include/exclude list), mirror-clones from source and mirror-pushes to destination via the `git` CLI over subprocess, authenticating over HTTPS using the resolved PAT as the git credential.
- **Identity mapper**: resolves a source identity to a destination identity via `identity_map`; returns an "unmapped" result rather than raising, so callers can flag it in the plan report instead of failing the item outright.
- **Permission/compatibility validator** (used by `plan` only): checks destination project existence, the `bypassRules` permission on the destination PAT, and process-template compatibility (does the destination have every work item type/field the source data will need).
- **State store**: SQLite-backed, keyed by `(entity_type, source_project, source_id)`, storing `destination_id` (nullable until known), `status` (`pending` / `migrated` / `failed`), `updated_at`, and `failure_reason` (nullable). Read by `status` and by every `apply_<entity>()` step to skip already-migrated items; written by every `apply_<entity>()` step as it progresses.
- **Report generator**: consumes the planned-item records produced by each service's `plan_<entity>()` step — `entity_type`, `source_id`, `title_or_name`, `planned_action` (`create` / `skip_already_migrated` / `flagged`), `flags` (list of strings) — and renders one HTML file: a summary-counts header plus a per-entity-type grouped table. Decoupled from entity-specific internals; it only depends on this shared record shape.
- **Orchestrator**: what the CLI subcommands call into. `plan` runs each service's plan step plus the validator, then hands the combined output to the report generator. `apply` runs the path service, then the work item service (both passes), then the repo service, honoring `--fail-fast`. `status` reads the state store and prints counts per entity type per status.

## Testing Decisions

- Tests target external behavior only — CLI command output, state store contents, generated HTML report contents/structure, resulting git repo contents — not internal implementation details of individual services.
- The one HTTP-level seam: all Azure DevOps REST API calls (via the SDK or raw `requests`) are intercepted in tests with the `responses` library against recorded/fixture JSON payloads (work item CRUD, comments, attachments, area/iteration path CRUD, project/process-template lookups, permission checks).
- Git repo migration is tested against real local repositories using `file://` temp-directory paths as source/destination stand-ins, exercising the actual `git` binary via subprocess — not mocked.
- Config loading/validation, the state store, the identity mapper, and the report generator are tested directly as near-pure units (their only I/O is the local filesystem/SQLite).
- Each domain service (path, work item, repo) has its own test module covering both its `plan_<entity>()` and `apply_<entity>()` behavior, including the idempotent-rerun case (a second `apply` is a no-op for already-migrated items) and the continue-vs-fail-fast behavior on a simulated item failure.
- No prior art in this repo — it's greenfield. This spec's testing approach establishes the first conventions rather than following an existing pattern.

## Out of Scope

- Pipelines (build/release definitions), wikis, test plans, service connections/variable groups, permissions/security groups — not migrated at all in v1.
- Azure DevOps Server/TFS (on-prem) — cloud (`dev.azure.com`) only.
- Development links (work item ↔ git commit/PR auto-association) — documented limitation, not implemented.
- Ongoing/repeated sync after an item is first migrated — this is a one-time migration tool; a `migrated` item (work item, path, or repo) is never revisited by a later run.
- Automatic creation of the destination project, or automatic remapping of mismatched work item types/fields between differing process templates — both are validated and reported by `plan`, but not automatically resolved.
- Live integration testing against a real Azure DevOps org — no sandbox org exists yet; deferred until one is available.

## Further Notes

The full round-by-round rationale behind these decisions (including alternatives considered and why they were rejected) lives in `docs/superpowers/specs/2026-09-03-ado-migration-framework.md` in this repo, alongside this ticket. The next step after triage is an implementation plan (bite-sized, TDD-style tasks) built from this spec.
