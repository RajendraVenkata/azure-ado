# 04: RealAdoClient — work item links

**What to build:** `RealAdoClient` support for reading and updating work item links against a real org, so cross-reference link rewriting has real data to operate on.

**Blocked by:** 03: RealAdoClient — work items (create, revision replay, attachments)

**Status:** ready-for-agent

- [x] `RealAdoClient`'s `list_work_items`/`get_work_item` return each work item's real links (work-item-to-work-item and pull-request references) as `Link` objects, matching the existing shape the link-rewriting migrator already consumes (`list_work_items` itself didn't exist before this ticket — added here via a WIQL query for all work item IDs in the project, then `get_work_item` per id)
- [x] `RealAdoClient` implements `update_work_item_links`, writing a resolved link set back to a real work item
- [ ] **Not yet done:** manual verification against a real org. What *was* verified in this session: `query_by_wiql`/`get_project` signatures via SDK introspection, and the PR artifact-URI parsing (`vstfs:///Git/PullRequestId/{projectId}%2F{repoId}%2F{prNumber}` → `Link(target="repoId:prNumber")`) round-trips correctly by direct invocation against a hand-built example URL.
- [x] This code is explicitly excluded from the automated test suite, per the spec's testing decision

**Known risk:** work-item-to-work-item links are always written as `System.LinkTypes.Related` regardless of the original relation type (Related, Parent/Child, Duplicate, etc.) — the source `Link` type in this codebase doesn't carry that distinction, only "work_item" vs "pull_request", so this is a deliberate simplification, not an oversight. If you need the original link-type semantics preserved, that would need a `Link.link_type` extension, which is out of scope here.
