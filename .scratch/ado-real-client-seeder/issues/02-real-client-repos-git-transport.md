# 02: RealAdoClient — repos + RealGitTransport

**What to build:** `RealAdoClient` support for listing and creating repositories, plus a `RealGitTransport` that performs actual git mirror clone/push, so a real repository with commit history can be migrated between two real Azure DevOps repos.

**Blocked by:** 01: RealAdoClient — area & iteration paths

**Status:** ready-for-agent

- [x] `RealAdoClient` implements `list_repos`/`create_repo` against the real API, returning `Repo` objects usable by the existing repo migrator unchanged
- [x] `RealGitTransport` implements `push_mirror` using real `git clone --mirror` (from the source URL) followed by `git push --mirror` (to the destination URL) — authenticated via a PAT injected as an `http.extraHeader` on each git invocation (kept out of the remote URL and out of any persisted git config)
- [x] Transient git/network failures (e.g. connection timeout) raise `TransientError`, so retry-with-backoff applies automatically
- [ ] **Not yet done:** manual verification of a full authenticated round-trip against two real Azure DevOps repositories (`list_repos`/`create_repo` via the real API, and an actual mirror push landing real commits on a real destination). What *was* verified in this session: `GitClient.get_repositories`/`create_repository` and `GitRepositoryCreateOptions`/`GitRepository` signatures via direct introspection of the installed SDK; and the `RealGitTransport` subprocess mechanics (temp dir, the `-c http.extraHeader=...` flag, mirror-clone ref layout) against a real public repo (`github.com/octocat/Hello-World` — clone only, no push, no ADO involved, no credentials needed) — confirmed 3535 refs correctly captured under `refs/heads/*` as expected for `--mirror`.
- [x] This code is explicitly excluded from the automated test suite, per the spec's testing decision
