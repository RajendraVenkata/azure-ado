# 13: Report-only artifact detection

**What to build:** Detecting the artifact types this framework deliberately does not migrate — classic release pipelines, dashboards, artifact feeds, and marketplace extensions in use — and listing them in the HTML report as a manual follow-up checklist. No destination writes occur for any of these.

**Blocked by:** 01: Core engine scaffolding

**Status:** ready-for-agent

- [x] Classic release pipeline definitions present in the source project are enumerated and listed in the report; none are created on the destination
- [x] Dashboards and their widgets present in the source project are enumerated and listed in the report; none are created on the destination
- [x] Artifact feeds owned/used by the source project are enumerated and listed in the report; no package content is copied
- [x] Marketplace extensions actually used by the source project (e.g. via referenced build tasks) are enumerated and listed in the report; none are installed on the destination org
- [x] This detection runs identically in dry-run and real-run modes (it never mutates the destination either way)
- [x] Covered by tests against the fake `AdoClient`
