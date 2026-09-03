# 01: Core engine scaffolding

**What to build:** The foundational CLI, config loading, client/transport abstractions, state file, and report skeleton that every later migrator plugs into. A migration operator can invoke the CLI against a config file in dry-run or real mode; with no artifact-type migrators wired in yet, it produces a valid (empty) state file and HTML report and exits cleanly, and re-running it is a no-op.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] CLI entrypoint accepts `migrate --config <path> [--dry-run]` and loads a YAML config describing source org/project, destination org/project, and PAT token environment-variable names (never literal token values in the file)
- [x] PAT values are resolved from the environment at runtime; a missing referenced environment variable produces a clear startup error
- [x] An `AdoClient` interface exists (SDK-backed where the SDK covers the operation, REST fallback otherwise) plus an in-memory fake implementation usable in tests without any network access
- [x] A `GitTransport` interface exists (mirror clone/push via git) plus a fake implementation usable in tests without invoking real git or network access
- [x] A local state file is read at startup and written after each unit of work, recording per-item completion status and a source-ID → destination-ID mapping table
- [x] Running the CLI twice in a row against the same fake backend and config produces identical state and makes no additional mutating calls on the second run
- [x] `--dry-run` produces an HTML report file and makes zero mutating calls against `AdoClient`/`GitTransport`; a real run makes mutating calls and updates state
- [x] The HTML report skeleton renders successfully with zero artifact types migrated (empty sections, no errors)
