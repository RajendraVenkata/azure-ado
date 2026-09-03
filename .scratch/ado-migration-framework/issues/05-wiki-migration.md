# 05: Wiki migration

**What to build:** Migrating the project wiki to the destination with full history, reusing the same git-mirror mechanism as regular repositories since Azure DevOps wikis are git-backed.

**Blocked by:** 04: Git repository migration

**Status:** ready-for-agent

- [ ] The project wiki's backing git repository is identified and migrated via the same `GitTransport` mirror clone/push path used for regular repos
- [ ] Destination wiki's full page history matches source after migration
- [ ] Migrated wiki is tracked in state; re-running skips it if already migrated
- [ ] A dry run lists the wiki that will be migrated in the HTML report
- [ ] Covered by tests against the fake `AdoClient`/`GitTransport`
