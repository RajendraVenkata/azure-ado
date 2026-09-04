# 01: RealAdoClient — area & iteration paths

**What to build:** A PAT-authenticated `RealAdoClient` that can list and create area paths and iteration paths against a real Azure DevOps project, establishing the authentication and transient-failure-mapping pattern that later `RealAdoClient` work builds on.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] `RealAdoClient` authenticates against a real Azure DevOps organization using a PAT resolved from an environment variable, the same way the rest of the tool resolves PATs (the client takes the already-resolved PAT string as a constructor argument — env-var resolution stays in `config.py`, called by whatever wires this client up, matching how the fakes are constructed today)
- [x] `RealAdoClient` implements `list_area_paths`/`create_area_path` and `list_iteration_paths`/`create_iteration_path` (including start/end dates) against the real API, returning the same domain types (`IterationPath`, etc.) the fakes and migrators already use
- [x] A rate-limiting (429) or server error (5xx) response from the real API raises the existing `TransientError`, so `DryRunGuard`'s retry-with-backoff applies automatically with no new retry logic
- [x] `RealAdoClient`'s mutating calls still go through the existing `DryRunGuard`/dry-run mechanism unchanged
- [ ] **Not yet done:** manual verification against a real Azure DevOps test organization. The code is written and excluded from the automated test suite (documented in `real_client.py`'s module docstring, not silent), and its construction/import path and exception-handling shape were sanity-checked against the real `dev.azure.com` API using an intentionally invalid PAT (confirmed the expected `AzureDevOpsServiceError` and that its message doesn't reliably carry an HTTP status code — hence the best-effort/persistent-by-default fallback in `_extract_status_code`). A full read/write pass against a real project with a valid PAT still needs to happen — that's on you, per the plan agreed for this ticket.

**Known risk:** the exact `azure-devops` SDK method signatures (`create_or_update_classification_node`, `get_classification_node`) and the `WorkItemClassificationNode`/`attributes` shape were verified by direct introspection of the installed SDK and one live (failing-auth) call against `dev.azure.com`, not a full successful round-trip. Small surprises (e.g. exact `path` separator behavior, attribute key casing) are plausible until a real create/read cycle is run.
