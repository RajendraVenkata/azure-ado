# 04: Git repository migration

**What to build:** Migrating a project's git repositories to the destination with full commit history intact, using git itself rather than the metadata API.

**Blocked by:** 01: Core engine scaffolding

**Status:** ready-for-agent

- [x] Each source repository is created on the destination via the API, then populated via `git clone --mirror` from source followed by `git push --mirror` to destination (through the `GitTransport` interface)
- [x] Destination repository's full commit history and branches match source after migration
- [x] Migrated repos are tracked in state (source repo → destination repo mapping); re-running skips repos already migrated
- [x] A dry run lists the repositories that will be migrated in the HTML report without invoking `GitTransport`
- [x] Covered by tests against the fake `AdoClient`/`GitTransport` — no real git operations or network access
