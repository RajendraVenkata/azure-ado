# 09: YAML build pipeline migration

**What to build:** Migrating YAML build pipeline definitions to the destination, with their repository and service-connection references remapped to the migrated destination equivalents.

**Blocked by:** 04: Git repository migration, 08: Service connection migration

**Status:** ready-for-agent

- [ ] Source YAML build pipeline definitions are read and recreated on the destination
- [ ] Any reference to a migrated repository within a pipeline definition is remapped to the destination repository, using the ID-mapping table
- [ ] Any reference to a migrated service connection within a pipeline definition is remapped to the destination connection, using the ID-mapping table
- [ ] Migrated pipelines are tracked in state; re-running skips pipelines already migrated
- [ ] A dry run lists the pipelines that will be migrated in the HTML report
- [ ] Covered by tests against the fake `AdoClient`
