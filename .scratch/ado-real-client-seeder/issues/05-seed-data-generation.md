# 05: Seed-data generation (pure)

**What to build:** A pure module that, given a work-item count, produces the full plan of test data to seed — independent of `RealAdoClient` entirely — so it can be fully unit tested without touching a real org.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] Given a work-item count, produces an area/iteration path tree that includes at least one nested path (to exercise hierarchy-ordering logic downstream)
- [x] Produces a commit plan for two repositories, each with 3-5 commits
- [x] Produces the requested number of work items (default around 10), each with a small number of revisions
- [x] At least one generated work item links to another generated work item
- [x] At least one generated work item links to a pull request reference within one of the generated repos' commit plans
- [x] At least one generated work item carries a file attachment
- [x] The generation function takes no `RealAdoClient`/`AdoClient` parameter and makes no network call — it returns plain data structures only
- [x] Covered by unit tests asserting on the shape of the returned plan (nesting present, commit counts, link presence, attachment presence) for a given count
