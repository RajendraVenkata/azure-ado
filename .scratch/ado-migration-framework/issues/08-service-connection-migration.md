# 08: Service connection migration

**What to build:** Best-effort recreation of the source project's service connections on the destination, ahead of pipeline migration which will reference them.

**Blocked by:** 01: Core engine scaffolding

**Status:** ready-for-agent

- [ ] Source service connections are read and recreated on the destination as far as the API allows
- [ ] Connection types/fields that can't be faithfully recreated (e.g. secrets that can't be read back via API) are handled with a clear, reported gap rather than a silent failure or fabricated value
- [ ] The source-ID → destination-ID mapping table in state is populated for each migrated service connection
- [ ] Migrated connections are tracked in state; re-running skips connections already migrated
- [ ] A dry run lists the service connections that will be migrated in the HTML report
- [ ] Covered by tests against the fake `AdoClient`
