# Azure DevOps Migration Framework — Spec

Captured from a grilling session on 2026-09-02/03. This is the shared understanding; the implementation plan (`docs/superpowers/plans/2026-09-03-ado-migration-framework.md`) argues from this document.

## Goal

A Python CLI framework that migrates Azure DevOps projects (work items, area/iteration paths, git repos) from a source organization to a destination organization, with a dry-run HTML report and idempotent, resumable execution via local state.

## Build approach & platform

- Custom Python framework built on the official `azure-devops` SDK (typed clients over the REST API); fall back to raw REST calls via `requests` only for endpoints the SDK doesn't cover.
- Azure DevOps **Services** (cloud, `dev.azure.com`) only. No on-prem Server/TFS support.

## Scope (v1)

In scope:
- **Work items**: standard + custom fields, links between work items (within scope — see below), attachments, current field state, full comment/discussion thread. No revision-by-revision history replay.
- **Area paths** and **iteration paths**, including iteration start/finish dates.
- **Git repositories**: code + all branches, no PR history. All non-disabled repos in a project are migrated by default; config may specify a per-project include/exclude list to override.

Explicitly out of scope for v1 (documented as known limitations):
- Pipelines (build/release definitions), wikis, test plans, service connections/variable groups, permissions/security groups.
- "Development" links (work item ↔ git commit/PR auto-detection) — destination work item IDs differ from source IDs, so ADO's commit-message auto-linking won't fire, and rewriting commit messages would break SHA preservation from the mirror push.
- Work item links whose target is outside the migration's scope (different project/org, or simply not selected in this run): the live ADO link relation is dropped; the target's URL/ID is preserved in the traceability comment, and the drop is flagged in the dry-run report as "link target not migrated".

## Configuration

YAML file. Shape:

```yaml
source:
  organization: https://dev.azure.com/source-org
  pat_env: ADO_SOURCE_PAT
destination:
  organization: https://dev.azure.com/dest-org
  pat_env: ADO_DEST_PAT
projects:
  - source_project: "Project A"
    destination_project: "Project A"
    repos:
      include: []   # empty = all non-disabled repos
      exclude: []
  - source_project: "Project B"
    destination_project: "Project B (Migrated)"
identity_map:
  alice@source.com: alice@dest.com
  bob@source.com: bob@dest.com
```

- PAT values are never written in the config — only the environment variable name holding them. A `.env` file is supported for local dev via `python-dotenv`. If a config value looks like a literal PAT (long opaque token string) rather than an env var name, fail fast with a clear error.
- The destination project **must already exist**. `plan` validates this and fails clearly if not — the tool never creates a destination project (process template/visibility/permissions are a deliberate admin decision).
- `identity_map` is required; entries cover every source identity that appears as `Assigned To` / `Created By` on an in-scope work item. Unmapped identities are not silently dropped or defaulted — they're flagged in the `plan` report.

## Work item fidelity

- Uses the Azure DevOps `bypassRules` option on work item writes to preserve original `CreatedBy`, `CreatedDate`, `ChangedDate`, and `State` directly, instead of letting the API stamp today's date/migration account and requiring valid workflow transitions for state.
- This requires the destination PAT's identity to hold the **"Bypass rules on work item updates"** permission on the destination project. `plan` proactively checks for this (not just discovered as a failure mid-`apply`).
- Assumes the destination project's process template already has matching work item types and fields to the source. `plan` validates this and reports any missing type/field as a flag; v1 does not implement a type/field remapping layer.
- Every migrated work item gets a comment on creation linking back to the source item's URL and ID, for traceability.

## State & idempotency

- Local **SQLite** state store (single file, e.g. `migration_state.db`).
- **One-time, freeze-and-migrate semantics**: once an item (work item, area/iteration path, or repo) is marked `migrated`, it is never revisited by a later `apply` run — no drift detection, no update-on-source-change. This applies uniformly to git repos too, even though git mirror pushes are naturally incremental — consistency with work-item semantics is preferred over that convenience.
- Per-item state: `pending` → `migrated` or `failed`, with enough identifying info (entity type, source ID, destination ID once known, timestamp, failure reason if any) to resume.
- On an item-level failure during `apply`: log it, mark the item `failed`, and continue with the rest of the run. A rerun retries only items in `pending` or `failed` state. An opt-in `--fail-fast` flag aborts the whole run on the first error instead.

## CLI

Single installable Python package:
- `pyproject.toml`, minimum Python **3.11**, console-script entry point `ado-migrate`.
- Built with `click`, subcommands:
  - `ado-migrate plan --config config.yaml` — dry run; validates config, connectivity, permissions (including `bypassRules`), process-template compatibility, identity mapping coverage; writes the HTML report; makes no writes to the destination.
  - `ado-migrate apply --config config.yaml [--fail-fast]` — executes the migration, honoring existing state (skips anything already `migrated`).
  - `ado-migrate status --config config.yaml` — reports current state store contents (counts per entity type per status).

## Dry-run HTML report

Produced by `plan`. Contents:
- Summary header: counts per entity type (work items, area/iteration paths, repos) broken down by planned action (create / already-migrated-skip / flagged).
- Full per-item table, grouped by entity type: ID, title/name, planned action, and any flags (unmapped identity, missing work item type/field, out-of-scope link target, missing `bypassRules` permission, etc.).

## Testing

No sandbox Azure DevOps org available yet. Test suite is built around mocked/recorded HTTP responses (no live-org integration tests in v1). Live-org validation is deferred until a sandbox org pair exists.
