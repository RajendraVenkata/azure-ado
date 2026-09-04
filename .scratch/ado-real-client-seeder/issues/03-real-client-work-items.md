# 03: RealAdoClient — work items (create, revision replay, attachments)

**What to build:** `RealAdoClient` support for creating a work item, replaying every subsequent revision as a real update, and attaching real file content — so work item revision history and attachments can be validated against the real API's actual semantics.

**Blocked by:** 01: RealAdoClient — area & iteration paths

**Status:** ready-for-agent

- [x] `RealAdoClient` implements `create_work_item` against the real API, returning a destination work item ID
- [x] `RealAdoClient` implements `update_work_item_fields` such that each call produces a new real revision on the destination work item, matching the existing revision-replay contract the work item migrator already relies on
- [x] `RealAdoClient` implements `add_attachment`, uploading real binary content and associating it with the work item
- [x] `RealAdoClient` implements `get_work_item` (read) returning the same `WorkItem` shape (revisions, attachments) the fakes and migrator already use
- [ ] **Not yet done:** manual verification of a real create-then-replay-then-attach-then-read round-trip against a real org. What *was* verified in this session: `create_work_item`/`update_work_item`/`get_work_item`/`get_revisions`/`create_attachment`/`get_attachment_content`/`JsonPatchOperation` signatures via direct introspection of the installed SDK, and the friendly-field-name ↔ ADO-reference-name mapping (`Title`↔`System.Title` etc.) round-trips correctly by direct invocation. A live create/update/attach/read cycle against a real project still needs to happen.
- [x] This code is explicitly excluded from the automated test suite, per the spec's testing decision

**Known risk:** the AttachedFile relation shape (`{"rel": "AttachedFile", "url": ..., "attributes": {"name": ...}}`) and the field-reference-name mapping (only `Title`/`State`/`AssignedTo`/`AreaPath`/`IterationPath`/`WorkItemType` are mapped; anything else is passed through as-is, so a custom field must already be given as its real ADO reference name, e.g. `"Custom.MyField"`) are both based on documented API shape, not a live-verified round-trip.
