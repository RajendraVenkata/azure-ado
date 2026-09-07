# ado-migrate

A Python CLI framework for migrating an Azure DevOps project (work items, area/iteration paths, git repos, and more) from a source organization to a destination organization, with resumable state and an HTML report.

## Requirements

- Python >= 3.10
- A destination Azure DevOps project that already exists (this tool never creates it)
- Personal Access Tokens (PATs) for the source and destination orgs, available as environment variables

## Install

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Windows (cmd.exe):

```bat
python -m venv .venv
.venv\Scripts\activate.bat
pip install -e ".[dev]"
```

This installs three console scripts: `migrate`, `seed-ado`, and `generate-identity-map`.

## Configure

Create a config YAML file (referenced below as `config.yaml`):

```yaml
source:
  organization_url: https://dev.azure.com/source-org
  project: MyProject
  pat_env: ADO_SOURCE_PAT
destination:
  organization_url: https://dev.azure.com/dest-org
  project: MyProject
  pat_env: ADO_DEST_PAT
```

`pat_env` names an environment variable holding the PAT — PAT values are never written in the config file itself. Set the referenced variables before running:

macOS/Linux:

```bash
export ADO_SOURCE_PAT=...
export ADO_DEST_PAT=...
```

Windows (PowerShell):

```powershell
$env:ADO_SOURCE_PAT = "..."
$env:ADO_DEST_PAT = "..."
```

Windows (cmd.exe):

```bat
set ADO_SOURCE_PAT=...
set ADO_DEST_PAT=...
```

Optionally, create an identity map file to translate source identities (e.g. email addresses) to their destination equivalents:

```yaml
mappings:
  alice@source.com: alice@dest.com
  bob@source.com: bob@dest.com
```

Any source identity not covered by the map is flagged in the report and replaced with an `unmapped-owner` placeholder rather than being silently dropped.

### Generate a starter identity.yaml

`generate-identity-map` connects to the source project and lists the identities with project-level permissions there — the same set shown under **Project Settings > Permissions > Users** in the Azure DevOps UI — then writes an `identity.yaml` with each one defaulted to itself. The file is valid to run immediately; you only need to edit the right-hand side of the entries that actually differ in the destination org.

macOS/Linux:

```bash
export MY_PAT=...
generate-identity-map --org https://dev.azure.com/source-org --pat-env MY_PAT --project MyProject --output identity.yaml
```

Windows (PowerShell):

```powershell
$env:MY_PAT = "..."
generate-identity-map --org https://dev.azure.com/source-org --pat-env MY_PAT --project MyProject --output identity.yaml
```

Windows (cmd.exe):

```bat
set MY_PAT=...
generate-identity-map --org https://dev.azure.com/source-org --pat-env MY_PAT --project MyProject --output identity.yaml
```

## Run a migration

```bash
migrate --config config.yaml
```

Flags:

- `--dry-run` — don't write to the destination; still produces the report.
- `--identity-map identity.yaml` — path to the identity map file described above.
- `--only work_items,repos` — comma-separated subset of artifact types to run (default: all). Valid types: `area_paths`, `iteration_paths`, `repos`, `wikis`, `service_connections`, `work_items`, `queries`, `pipelines`, `test_plans`, `security_groups`, `links`, `report_only`.

Output, written next to the config file:

- `state.json` — per-item migration state, used to resume/skip on subsequent runs.
- `report.html` — summary of what was migrated, skipped, or flagged.

## Seed a test org

`seed-ado` creates a throwaway Azure DevOps project in a real org and populates it with sample data, useful for exercising a migration end to end:

macOS/Linux:

```bash
export MY_PAT=...
seed-ado --org https://dev.azure.com/my-org --pat-env MY_PAT --project-prefix ado-migrate-test
```

Windows (PowerShell):

```powershell
$env:MY_PAT = "..."
seed-ado --org https://dev.azure.com/my-org --pat-env MY_PAT --project-prefix ado-migrate-test
```

Windows (cmd.exe):

```bat
set MY_PAT=...
seed-ado --org https://dev.azure.com/my-org --pat-env MY_PAT --project-prefix ado-migrate-test
```

This writes `seeded-config.yaml` with the `source` section filled in; fill in the `destination` section before running `migrate` against it.

## Run tests

```bash
pytest
```

## Known limitations

- v1 scope excludes pipelines, wikis, test plans, service connections, and security groups migration logic beyond what's flagged in the report; see `docs/superpowers/specs/2026-09-03-ado-migration-framework.md` for the full scope discussion.
- The `migrate` CLI entry point (`src/ado_migrate/cli.py`) currently wires up the abstract `AdoClient`/`GitTransport` base classes rather than `RealAdoClient`/`RealGitTransport`, so it is not yet wired for live-org runs — `seed-ado` and `generate-identity-map` are the only entry points currently exercising the real Azure DevOps SDK client.
