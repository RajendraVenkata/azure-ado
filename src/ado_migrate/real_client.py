"""Real Azure DevOps API-backed AdoClient.

Deliberately excluded from the automated test suite (see spec
ado-real-client-seeder, ticket 01): every method here makes a real HTTP
call to the Azure DevOps REST API via the `azure-devops` SDK, and this
codebase's established convention is to test only against fakes, never a
real org. Verification of this module is manual — run it against a real
Azure DevOps organization.
"""

import io
import re
from datetime import date, datetime
from typing import Any, Optional
from urllib.parse import urlparse

import requests
from azure.devops.connection import Connection
from azure.devops.exceptions import AzureDevOpsClientRequestError
from azure.devops.v7_1.dashboard.models import TeamContext as DashboardTeamContext
from azure.devops.v7_1.git.models import GitRepositoryCreateOptions
from azure.devops.v7_1.graph.models import (
    GraphSubjectLookup,
    GraphSubjectLookupKey,
    GraphSubjectQuery,
)
from azure.devops.v7_1.service_endpoint.models import (
    EndpointAuthorization,
    ProjectReference,
    ServiceEndpoint,
    ServiceEndpointProjectReference,
)
from azure.devops.v7_1.test_plan.models import (
    SuiteTestCaseCreateUpdateParameters,
    TestPlanCreateParams,
    TestSuiteCreateParams,
    TestSuiteReference,
)
from azure.devops.v7_1.test_plan.models import WorkItem as TestPlanWorkItemRef
from azure.devops.v7_1.wiki.models import WikiCreateParametersV2
from azure.devops.v7_1.work_item_tracking.models import (
    JsonPatchOperation,
    QueryHierarchyItem,
    TeamContext,
    Wiql,
    WorkItemClassificationNode,
)
from msrest.authentication import BasicAuthentication

from ado_migrate.client import (
    AdoClient,
    ArtifactFeed,
    Attachment,
    Dashboard,
    Extension,
    IterationPath,
    Link,
    Pipeline,
    Query,
    ReleasePipeline,
    Repo,
    SecurityGroup,
    ServiceConnection,
    TestPlan,
    TestSuite,
    WorkItem,
)
from ado_migrate.mutation import TransientError

_FIELD_REFERENCE_NAMES = {
    "Title": "System.Title",
    "State": "System.State",
    "AssignedTo": "System.AssignedTo",
    "AreaPath": "System.AreaPath",
    "IterationPath": "System.IterationPath",
    "WorkItemType": "System.WorkItemType",
}
_FRIENDLY_FIELD_NAMES = {v: k for k, v in _FIELD_REFERENCE_NAMES.items()}

_WIT_CLIENT_PATH = (
    "azure.devops.v7_1.work_item_tracking.work_item_tracking_client.WorkItemTrackingClient"
)
_GIT_CLIENT_PATH = "azure.devops.v7_1.git.git_client.GitClient"
_CORE_CLIENT_PATH = "azure.devops.v7_1.core.core_client.CoreClient"
_GRAPH_CLIENT_PATH = "azure.devops.v7_1.graph.graph_client.GraphClient"
_WIKI_CLIENT_PATH = "azure.devops.v7_1.wiki.wiki_client.WikiClient"
_SERVICE_ENDPOINT_CLIENT_PATH = (
    "azure.devops.v7_1.service_endpoint.service_endpoint_client.ServiceEndpointClient"
)
_TEST_PLAN_CLIENT_PATH = "azure.devops.v7_1.test_plan.test_plan_client.TestPlanClient"
_RELEASE_CLIENT_PATH = "azure.devops.v7_1.release.release_client.ReleaseClient"
_DASHBOARD_CLIENT_PATH = "azure.devops.v7_1.dashboard.dashboard_client.DashboardClient"
_FEED_CLIENT_PATH = "azure.devops.v7_1.feed.feed_client.FeedClient"
_EXTENSION_MANAGEMENT_CLIENT_PATH = (
    "azure.devops.v7_1.extension_management.extension_management_client."
    "ExtensionManagementClient"
)
_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
_STATUS_CODE_IN_MESSAGE = re.compile(r"returned a (\d+) status code")

# Built-in groups every Azure DevOps project already has by default; these
# are never migrated since they already exist in the destination project.
_DEFAULT_SECURITY_GROUP_NAMES = {
    "Project Administrators",
    "Contributors",
    "Readers",
    "Build Administrators",
    "Release Administrators",
    "Endpoint Administrators",
    "Endpoint Creators",
    "Project Valid Users",
    "Project-Scoped Users",
}


class RealAdoClient(AdoClient):
    def __init__(self, organization_url: str, pat: str, dry_run: bool = False):
        super().__init__(dry_run)
        connection = Connection(
            base_url=organization_url, creds=BasicAuthentication("", pat)
        )
        self._wit_client = connection.get_client(_WIT_CLIENT_PATH)
        self._git_client = connection.get_client(_GIT_CLIENT_PATH)
        self._core_client = connection.get_client(_CORE_CLIENT_PATH)
        self._graph_client = connection.get_client(_GRAPH_CLIENT_PATH)
        self._wiki_client = connection.get_client(_WIKI_CLIENT_PATH)
        self._service_endpoint_client = connection.get_client(_SERVICE_ENDPOINT_CLIENT_PATH)
        self._test_plan_client = connection.get_client(_TEST_PLAN_CLIENT_PATH)
        self._release_client = connection.get_client(_RELEASE_CLIENT_PATH)
        self._dashboard_client = connection.get_client(_DASHBOARD_CLIENT_PATH)
        self._feed_client = connection.get_client(_FEED_CLIENT_PATH)
        self._extension_management_client = connection.get_client(
            _EXTENSION_MANAGEMENT_CLIENT_PATH
        )
        self._pat = pat
        self._organization_url = organization_url.rstrip("/")
        self._project_id_cache: dict[str, str] = {}
        self._test_plan_root_suite_cache: dict[str, str] = {}

    def list_area_paths(self, project: str) -> list[str]:
        root = self._call(
            self._wit_client.get_classification_node, project, "areas", depth=1000
        )
        return _flatten_paths(root)

    def create_area_path(self, project: str, path: str) -> Optional[str]:
        def do_create() -> str:
            leaf_name, parent_path = _split_leaf(path)
            self._call(
                self._wit_client.create_or_update_classification_node,
                WorkItemClassificationNode(name=leaf_name),
                project,
                "areas",
                path=parent_path or None,
            )
            return path

        return self._mutate(f"create area path '{path}' in {project}", do_create)

    def list_iteration_paths(self, project: str) -> list[IterationPath]:
        root = self._call(
            self._wit_client.get_classification_node, project, "iterations", depth=1000
        )
        return _flatten_iteration_paths(root)

    def create_iteration_path(
        self,
        project: str,
        path: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[str]:
        def do_create() -> str:
            leaf_name, parent_path = _split_leaf(path)
            attributes: dict[str, Any] = {}
            if start_date:
                attributes["startDate"] = start_date
            if end_date:
                attributes["finishDate"] = end_date

            self._call(
                self._wit_client.create_or_update_classification_node,
                WorkItemClassificationNode(
                    name=leaf_name, attributes=attributes or None
                ),
                project,
                "iterations",
                path=parent_path or None,
            )
            return path

        return self._mutate(f"create iteration path '{path}' in {project}", do_create)

    def list_repos(self, project: str) -> list[Repo]:
        repos = self._call(self._git_client.get_repositories, project)
        return [Repo(id=r.id, name=r.name, clone_url=r.remote_url) for r in repos]

    def create_repo(self, project: str, name: str) -> Optional[Repo]:
        def do_create() -> Repo:
            created = self._call(
                self._git_client.create_repository,
                GitRepositoryCreateOptions(name=name),
                project=project,
            )
            return Repo(id=created.id, name=created.name, clone_url=created.remote_url)

        return self._mutate(f"create repo '{name}' in {project}", do_create)

    def create_work_item(
        self, project: str, work_item_type: str, fields: dict[str, Any]
    ) -> Optional[str]:
        def do_create() -> str:
            document = _fields_to_patch_document(fields)
            created = self._call(
                self._wit_client.create_work_item, document, project, work_item_type
            )
            return str(created.id)

        return self._mutate(f"create {work_item_type} in {project}", do_create)

    def update_work_item_fields(
        self, project: str, destination_id: str, fields: dict[str, Any]
    ) -> None:
        def do_update() -> None:
            document = _fields_to_patch_document(fields)
            self._call(
                self._wit_client.update_work_item,
                document,
                int(destination_id),
                project=project,
            )

        self._mutate(f"update work item {destination_id} in {project}", do_update)

    def add_attachment(
        self, project: str, destination_id: str, attachment: Attachment
    ) -> None:
        def do_add() -> None:
            uploaded = self._call(
                self._wit_client.create_attachment,
                io.BytesIO(attachment.content),
                project=project,
                file_name=attachment.name,
            )
            document = [
                JsonPatchOperation(
                    op="add",
                    path="/relations/-",
                    value={
                        "rel": "AttachedFile",
                        "url": uploaded.url,
                        "attributes": {"name": attachment.name},
                    },
                )
            ]
            self._call(
                self._wit_client.update_work_item,
                document,
                int(destination_id),
                project=project,
            )

        self._mutate(
            f"add attachment '{attachment.name}' to work item {destination_id} in {project}",
            do_add,
        )

    def list_work_items(self, project: str) -> list[WorkItem]:
        return [
            self.get_work_item(project, str(work_item_id))
            for work_item_id in self._list_work_item_ids(project)
        ]

    def _list_work_item_ids(self, project: str) -> list[int]:
        # Azure DevOps caps WIQL results at 20000 rows per query (VS402337),
        # so projects above that size must be paged by System.Id. The
        # [System.TeamProject] = @project clause is required here even
        # though team_context is also set below — team_context alone does
        # not reliably scope a custom WIQL query to one project, and
        # without it this silently queries the whole organization.
        page_size = 19999
        ids: list[int] = []
        last_id = 0
        while True:
            result = self._call(
                self._wit_client.query_by_wiql,
                Wiql(
                    query=(
                        "SELECT [System.Id] FROM WorkItems "
                        f"WHERE [System.TeamProject] = @project AND [System.Id] > {last_id} "
                        "ORDER BY [System.Id] ASC"
                    )
                ),
                team_context=TeamContext(project=project),
                top=page_size,
            )
            page = [item.id for item in (result.work_items or [])]
            if not page:
                break
            ids.extend(page)
            last_id = page[-1]
            if len(page) < page_size:
                break
        return ids

    def get_work_item(self, project: str, destination_id: str) -> WorkItem:
        revisions_raw = self._call(
            self._wit_client.get_revisions, int(destination_id), project=project
        )
        revisions = [_friendlify_fields(r.fields) for r in revisions_raw]

        current = self._call(
            self._wit_client.get_work_item,
            int(destination_id),
            project=project,
            expand="relations",
        )
        work_item_type = (current.fields or {}).get("System.WorkItemType", "")
        relations = current.relations or []

        attachments = [
            self._download_attachment(project, rel)
            for rel in relations
            if rel.rel == "AttachedFile"
        ]
        links = _parse_links(relations)

        return WorkItem(
            id=destination_id,
            work_item_type=work_item_type,
            revisions=revisions,
            attachments=attachments,
            links=links,
        )

    def update_work_item_links(
        self, project: str, destination_id: str, links: list[Link]
    ) -> None:
        def do_update() -> None:
            document = [self._link_to_patch_operation(project, link) for link in links]
            if document:
                self._call(
                    self._wit_client.update_work_item,
                    document,
                    int(destination_id),
                    project=project,
                )

        self._mutate(f"update links on work item {destination_id} in {project}", do_update)

    def _link_to_patch_operation(self, project: str, link: Link) -> JsonPatchOperation:
        if link.link_type == "work_item":
            value = {
                "rel": "System.LinkTypes.Related",
                "url": f"{self._organization_url}/_apis/wit/workItems/{link.target}",
            }
        elif link.link_type == "pull_request":
            repo_id, _, pr_number = link.target.partition(":")
            project_id = self._get_project_id(project)
            value = {
                "rel": "ArtifactLink",
                "url": f"vstfs:///Git/PullRequestId/{project_id}%2F{repo_id}%2F{pr_number}",
            }
        else:
            raise ValueError(f"Unknown link type: {link.link_type}")

        return JsonPatchOperation(op="add", path="/relations/-", value=value)

    def _get_project_id(self, project: str) -> str:
        if project not in self._project_id_cache:
            team_project = self._call(self._core_client.get_project, project)
            self._project_id_cache[project] = team_project.id
        return self._project_id_cache[project]

    def list_project_users(self, project: str) -> list[str]:
        """Identities with a materialized membership in the project's scope.

        Mirrors what Project Settings > Permissions > Users shows in the
        Azure DevOps UI (direct project members, not the security groups
        themselves).
        """
        project_id = self._get_project_id(project)
        project_descriptor = self._call(self._graph_client.get_descriptor, project_id).value

        identities: list[str] = []
        continuation_token = None
        while True:
            page = self._call(
                self._graph_client.list_users,
                scope_descriptor=project_descriptor,
                continuation_token=continuation_token,
            )
            for user in page.graph_users or []:
                identity = user.principal_name or user.mail_address
                if identity:
                    identities.append(identity)

            continuation_token = page.continuation_token
            if not continuation_token:
                break

        return identities

    def list_wikis(self, project: str) -> list[Repo]:
        wikis = self._call(self._wiki_client.get_all_wikis, project=project)
        return [Repo(id=w.id, name=w.name, clone_url=w.remote_url) for w in (wikis or [])]

    def create_wiki(self, project: str, name: str) -> Optional[Repo]:
        def do_create() -> Repo:
            project_id = self._get_project_id(project)
            # A code wiki is backed by its own git repo; create that repo
            # first so the caller's subsequent push_mirror() has somewhere
            # to push the mirrored wiki content.
            repo = self._call(
                self._git_client.create_repository,
                GitRepositoryCreateOptions(name=name),
                project=project,
            )
            wiki = self._call(
                self._wiki_client.create_wiki,
                WikiCreateParametersV2(
                    name=name,
                    project_id=project_id,
                    repository_id=repo.id,
                    type="codeWiki",
                    mapped_path="/",
                ),
                project=project,
            )
            return Repo(id=wiki.id, name=wiki.name, clone_url=wiki.remote_url)

        return self._mutate(f"create wiki '{name}' in {project}", do_create)

    def list_service_connections(self, project: str) -> list[ServiceConnection]:
        endpoints = self._call(
            self._service_endpoint_client.get_service_endpoints, project, include_details=True
        )
        result = []
        for endpoint in endpoints or []:
            auth = endpoint.authorization
            scheme = (auth.scheme if auth else None) or "None"
            # Azure DevOps never returns real secret values on read (they
            # come back redacted or omitted entirely), so any endpoint with
            # a non-"None" auth scheme is conservatively flagged as
            # secret-bearing and reported as needing manual re-entry.
            has_secret = scheme != "None"
            result.append(
                ServiceConnection(
                    id=endpoint.id,
                    name=endpoint.name,
                    connection_type=endpoint.type,
                    config={
                        "scheme": scheme,
                        "parameters": dict(auth.parameters or {}) if auth else {},
                        "url": endpoint.url,
                    },
                    has_secret=has_secret,
                )
            )
        return result

    def create_service_connection(
        self,
        project: str,
        name: str,
        connection_type: str,
        config: dict[str, Any],
        has_secret: bool = False,
    ) -> Optional[ServiceConnection]:
        def do_create() -> ServiceConnection:
            project_id = self._get_project_id(project)
            scheme = config.get("scheme", "None")
            # Secret parameter values never round-trip through the read API
            # (see list_service_connections), so a secret-bearing endpoint
            # is created with empty credentials and must be re-entered
            # manually afterward — the report already flags this.
            parameters = {} if has_secret else dict(config.get("parameters", {}))
            endpoint = ServiceEndpoint(
                name=name,
                type=connection_type,
                url=config.get("url"),
                authorization=EndpointAuthorization(scheme=scheme, parameters=parameters),
                service_endpoint_project_references=[
                    ServiceEndpointProjectReference(
                        name=name,
                        project_reference=ProjectReference(id=project_id, name=project),
                    )
                ],
            )
            created = self._call(
                self._service_endpoint_client.create_service_endpoint, endpoint
            )
            return ServiceConnection(
                id=created.id,
                name=created.name,
                connection_type=created.type,
                config=dict(config),
                has_secret=has_secret,
            )

        return self._mutate(
            f"create service connection '{name}' in {project}", do_create
        )

    def list_queries(self, project: str) -> list[Query]:
        roots = self._call(self._wit_client.get_queries, project, expand="all", depth=2)
        queries: list[Query] = []
        for root in roots or []:
            self._collect_queries(project, root, queries)
        return queries

    def _collect_queries(self, project: str, item, queries: list[Query]) -> None:
        if not item.is_folder:
            path = item.path or item.name
            folder_path = path.rsplit("/", 1)[0] if "/" in path else ""
            queries.append(
                Query(id=item.id, name=item.name, folder_path=folder_path, wiql=item.wiql or "")
            )
            return

        children = item.children
        if not children and item.has_children:
            # get_queries()'s depth limit didn't expand this folder; fetch
            # it directly.
            expanded = self._call(
                self._wit_client.get_query, project, item.path, expand="all", depth=2
            )
            children = expanded.children

        for child in children or []:
            self._collect_queries(project, child, queries)

    def create_query(
        self, project: str, name: str, folder_path: str, wiql: str
    ) -> Optional[Query]:
        def do_create() -> Query:
            # Nested folders are not pre-created here; the destination
            # folder_path must already exist (e.g. a prior sibling query in
            # the same folder already created it, or it's a default root
            # like "Shared Queries"). A missing intermediate folder makes
            # this call fail, which is reported like any other item failure.
            created = self._call(
                self._wit_client.create_query,
                QueryHierarchyItem(name=name, wiql=wiql, is_folder=False),
                project,
                folder_path or "Shared Queries",
            )
            return Query(id=created.id, name=created.name, folder_path=folder_path, wiql=wiql)

        return self._mutate(f"create query '{name}' in {project}", do_create)

    def list_pipelines(self, project: str) -> list[Pipeline]:
        listing = self._raw_request(
            "GET", f"{self._organization_url}/{project}/_apis/pipelines", {"api-version": "7.1"}
        )
        pipelines = []
        for summary in (listing or {}).get("value", []):
            detail = self._raw_request(
                "GET",
                f"{self._organization_url}/{project}/_apis/pipelines/{summary['id']}",
                {"api-version": "7.1"},
            )
            configuration = detail.get("configuration") or {}
            repository = configuration.get("repository") or {}
            pipelines.append(
                Pipeline(
                    id=str(detail["id"]),
                    name=detail["name"],
                    yaml_path=configuration.get("path", ""),
                    repo_id=repository.get("id", ""),
                    # Service connections referenced inside a pipeline's
                    # YAML (task inputs, resources) aren't enumerable via
                    # this API without parsing the YAML file itself.
                    service_connection_ids=[],
                )
            )
        return pipelines

    def create_pipeline(
        self,
        project: str,
        name: str,
        yaml_path: str,
        repo_id: str,
        service_connection_ids: list[str],
    ) -> Optional[Pipeline]:
        def do_create() -> Pipeline:
            body = {
                "name": name,
                "configuration": {
                    "type": "yaml",
                    "path": yaml_path,
                    "repository": {"id": repo_id, "type": "azureReposGit"},
                },
            }
            created = self._raw_request(
                "POST",
                f"{self._organization_url}/{project}/_apis/pipelines",
                {"api-version": "7.1"},
                json_body=body,
            )
            return Pipeline(
                id=str(created["id"]),
                name=created["name"],
                yaml_path=yaml_path,
                repo_id=repo_id,
                service_connection_ids=list(service_connection_ids),
            )

        return self._mutate(f"create pipeline '{name}' in {project}", do_create)

    def list_test_plans(self, project: str) -> list[TestPlan]:
        plans = self._call(self._test_plan_client.get_test_plans, project) or []
        result = []
        for plan in plans:
            raw_suites = (
                self._call(self._test_plan_client.get_test_suites_for_plan, project, plan.id)
                or []
            )
            suites = []
            for suite in raw_suites:
                if suite.parent_suite is None:
                    # The plan's auto-created root suite; recreated
                    # automatically when the destination plan is created.
                    continue
                entries = (
                    self._call(self._test_plan_client.get_suite_entries, project, suite.id)
                    or []
                )
                test_case_ids = [
                    str(entry.id)
                    for entry in entries
                    if (entry.suite_entry_type or "").lower() == "testcase"
                ]
                suites.append(
                    TestSuite(
                        id=str(suite.id),
                        name=suite.name,
                        parent_suite_id=(
                            str(suite.parent_suite.id) if suite.parent_suite.id else None
                        ),
                        test_case_ids=test_case_ids,
                        configuration_names=[
                            c.name for c in (suite.default_configurations or []) if c.name
                        ],
                    )
                )
            result.append(TestPlan(id=str(plan.id), name=plan.name, suites=suites))
        return result

    def create_test_plan(self, project: str, name: str) -> Optional[TestPlan]:
        def do_create() -> TestPlan:
            created = self._call(
                self._test_plan_client.create_test_plan,
                TestPlanCreateParams(name=name),
                project,
            )
            return TestPlan(id=str(created.id), name=created.name, suites=[])

        return self._mutate(f"create test plan '{name}' in {project}", do_create)

    def create_test_suite(
        self,
        project: str,
        plan_id: str,
        name: str,
        parent_suite_id: Optional[str],
        test_case_ids: list[str],
        configuration_names: list[str],
    ) -> Optional[TestSuite]:
        def do_create() -> TestSuite:
            parent_id = parent_suite_id or self._get_test_plan_root_suite_id(project, plan_id)
            created = self._call(
                self._test_plan_client.create_test_suite,
                TestSuiteCreateParams(
                    name=name,
                    parent_suite=TestSuiteReference(id=int(parent_id)),
                    suite_type="staticTestSuite",
                ),
                project,
                plan_id,
            )
            if test_case_ids:
                self._call(
                    self._test_plan_client.add_test_cases_to_suite,
                    [
                        SuiteTestCaseCreateUpdateParameters(
                            work_item=TestPlanWorkItemRef(id=int(tc_id))
                        )
                        for tc_id in test_case_ids
                    ],
                    project,
                    plan_id,
                    created.id,
                )
            return TestSuite(
                id=str(created.id),
                name=created.name,
                parent_suite_id=parent_suite_id,
                test_case_ids=list(test_case_ids),
                configuration_names=list(configuration_names),
            )

        return self._mutate(f"create test suite '{name}' in {project}", do_create)

    def _get_test_plan_root_suite_id(self, project: str, plan_id: str) -> str:
        if plan_id not in self._test_plan_root_suite_cache:
            suites = (
                self._call(self._test_plan_client.get_test_suites_for_plan, project, plan_id)
                or []
            )
            root = next(s for s in suites if s.parent_suite is None)
            self._test_plan_root_suite_cache[plan_id] = str(root.id)
        return self._test_plan_root_suite_cache[plan_id]

    def list_security_groups(self, project: str) -> list[SecurityGroup]:
        project_id = self._get_project_id(project)
        project_descriptor = self._call(self._graph_client.get_descriptor, project_id).value
        groups = self._call(self._graph_client.list_groups, scope_descriptor=project_descriptor)

        result = []
        for group in groups.graph_groups or []:
            if group.display_name in _DEFAULT_SECURITY_GROUP_NAMES:
                continue

            memberships = (
                self._call(
                    self._graph_client.list_memberships, group.descriptor, direction="down"
                )
                or []
            )
            member_descriptors = [m.member_descriptor for m in memberships]
            member_identities = []
            if member_descriptors:
                subjects = self._call(
                    self._graph_client.lookup_subjects,
                    GraphSubjectLookup(
                        lookup_keys=[
                            GraphSubjectLookupKey(descriptor=d) for d in member_descriptors
                        ]
                    ),
                )
                for subject in (subjects or {}).values():
                    # Nested-group members are skipped; only direct user
                    # members are migrated, consistent with
                    # list_project_users().
                    if getattr(subject, "subject_kind", None) != "user":
                        continue
                    identity = getattr(subject, "principal_name", None) or getattr(
                        subject, "mail_address", None
                    )
                    if identity:
                        member_identities.append(identity)

            result.append(
                SecurityGroup(
                    id=group.descriptor,
                    name=group.display_name,
                    member_identities=member_identities,
                )
            )
        return result

    def create_security_group(
        self, project: str, name: str, member_identities: list[str]
    ) -> Optional[SecurityGroup]:
        def do_create() -> SecurityGroup:
            project_id = self._get_project_id(project)
            project_descriptor = self._call(
                self._graph_client.get_descriptor, project_id
            ).value
            # The SDK's GraphGroupCreationContext model only supports
            # storage-key-based creation (its own docstring says not to use
            # it to create a new group); creating a native ADO group by
            # display name needs the raw REST body the SDK doesn't model.
            created = self._raw_request(
                "POST",
                f"{self._graph_base_url}/_apis/graph/groups",
                {"scopeDescriptor": project_descriptor, "api-version": "7.1-preview.1"},
                json_body={"displayName": name},
            )
            group_descriptor = created["descriptor"]
            for identity in member_identities:
                member_descriptor = self._resolve_user_descriptor(identity)
                if member_descriptor:
                    self._call(
                        self._graph_client.add_membership, member_descriptor, group_descriptor
                    )
            return SecurityGroup(
                id=group_descriptor,
                name=created["displayName"],
                member_identities=list(member_identities),
            )

        return self._mutate(f"create security group '{name}' in {project}", do_create)

    def _resolve_user_descriptor(self, principal_name: str) -> Optional[str]:
        matches = self._call(
            self._graph_client.query_subjects,
            GraphSubjectQuery(query=principal_name, subject_kind=["User"]),
        )
        return matches[0].descriptor if matches else None

    def list_release_pipelines(self, project: str) -> list[ReleasePipeline]:
        definitions = self._call(self._release_client.get_release_definitions, project)
        return [ReleasePipeline(id=str(d.id), name=d.name) for d in (definitions or [])]

    def list_dashboards(self, project: str) -> list[Dashboard]:
        dashboards = self._call(
            self._dashboard_client.get_dashboards_by_project,
            DashboardTeamContext(project=project),
        )
        return [
            Dashboard(
                id=d.id,
                name=d.name,
                widgets=[w.name or w.id for w in (d.widgets or [])],
            )
            for d in (dashboards or [])
        ]

    def list_artifact_feeds(self, project: str) -> list[ArtifactFeed]:
        feeds = self._call(self._feed_client.get_feeds, project=project)
        return [ArtifactFeed(id=f.id, name=f.name) for f in (feeds or [])]

    def list_used_extensions(self, project: str) -> list[Extension]:
        # Extensions are installed at the organization level in Azure
        # DevOps, not per-project, so `project` has no effect on this list.
        extensions = self._call(self._extension_management_client.get_installed_extensions)
        return [
            Extension(id=e.extension_id, name=e.extension_name) for e in (extensions or [])
        ]

    def _download_attachment(self, project: str, relation) -> Attachment:
        attachment_id = urlparse(relation.url).path.rstrip("/").split("/")[-1]
        name = (relation.attributes or {}).get("name", attachment_id)
        chunks = self._call(
            self._wit_client.get_attachment_content,
            attachment_id,
            project=project,
            file_name=name,
        )
        return Attachment(name=name, content=b"".join(chunks))

    def _call(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            raise TransientError(str(exc)) from exc
        except AzureDevOpsClientRequestError as exc:
            # The SDK's exception types don't reliably expose the HTTP status
            # code as an attribute (only sometimes in the message text), so
            # this is a best-effort extraction. When we can't tell, we treat
            # the failure as persistent rather than risk silently retrying a
            # genuine (non-transient) error.
            status_code = _extract_status_code(exc)
            if status_code in _TRANSIENT_STATUS_CODES:
                raise TransientError(str(exc)) from exc
            raise

    @property
    def _graph_base_url(self) -> str:
        # The Graph API is hosted on a dedicated vssps subdomain rather
        # than dev.azure.com.
        org_name = urlparse(self._organization_url).path.strip("/")
        return f"https://vssps.dev.azure.com/{org_name}"

    def _raw_request(
        self,
        method: str,
        url: str,
        params: dict[str, str],
        json_body: Optional[dict] = None,
    ) -> Any:
        """Fallback for endpoints the typed SDK models can't fully express
        (see spec: "fall back to raw REST calls via requests only for
        endpoints the SDK doesn't cover")."""

        def do_call():
            response = requests.request(
                method,
                url,
                params=params,
                json=json_body,
                auth=("", self._pat),
                timeout=100,
            )
            if response.status_code in _TRANSIENT_STATUS_CODES:
                raise TransientError(
                    f"{method} {url} -> {response.status_code}: {response.text}"
                )
            response.raise_for_status()
            return response.json() if response.content else None

        return self._call(do_call)


def _split_leaf(path: str) -> tuple[str, str]:
    segments = path.split("/")
    return segments[-1], "\\".join(segments[:-1])


def _flatten_paths(node: WorkItemClassificationNode, prefix: str = "") -> list[str]:
    paths = []
    for child in node.children or []:
        child_path = f"{prefix}{child.name}"
        paths.append(child_path)
        paths.extend(_flatten_paths(child, prefix=f"{child_path}/"))
    return paths


def _flatten_iteration_paths(
    node: WorkItemClassificationNode, prefix: str = ""
) -> list[IterationPath]:
    result = []
    for child in node.children or []:
        child_path = f"{prefix}{child.name}"
        attributes = child.attributes or {}
        result.append(
            IterationPath(
                path=child_path,
                start_date=_format_date(attributes.get("startDate")),
                end_date=_format_date(attributes.get("finishDate")),
            )
        )
        result.extend(_flatten_iteration_paths(child, prefix=f"{child_path}/"))
    return result


def _format_date(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


def _extract_status_code(exc: Exception) -> Optional[int]:
    match = _STATUS_CODE_IN_MESSAGE.search(str(exc))
    return int(match.group(1)) if match else None


def _fields_to_patch_document(fields: dict[str, Any]) -> list[JsonPatchOperation]:
    return [
        JsonPatchOperation(
            op="add", path=f"/fields/{_FIELD_REFERENCE_NAMES.get(key, key)}", value=value
        )
        for key, value in fields.items()
    ]


def _friendlify_fields(fields: Optional[dict[str, Any]]) -> dict[str, Any]:
    result = {}
    for reference_name, value in (fields or {}).items():
        if reference_name == "System.AssignedTo":
            value = _identity_ref_to_string(value)
        result[_FRIENDLY_FIELD_NAMES.get(reference_name, reference_name)] = value
    return result


def _identity_ref_to_string(value: Any) -> Any:
    """Identity-typed fields (e.g. AssignedTo) come back from the REST API as
    an IdentityRef object, not a plain string. Reduce it to the identity
    string the rest of the pipeline (identity map resolution) expects."""
    if isinstance(value, dict):
        return value.get("uniqueName") or value.get("displayName") or value
    return value


def _parse_links(relations: list) -> list[Link]:
    links = []
    for rel in relations:
        if rel.rel == "AttachedFile":
            continue
        if rel.rel.startswith("System.LinkTypes."):
            target_id = rel.url.rstrip("/").split("/")[-1]
            links.append(Link(link_type="work_item", target=target_id))
        elif rel.rel == "ArtifactLink" and "/PullRequestId/" in rel.url:
            links.append(Link(link_type="pull_request", target=_parse_pr_artifact_uri(rel.url)))
    return links


def _parse_pr_artifact_uri(url: str) -> str:
    # vstfs:///Git/PullRequestId/{projectId}%2F{repositoryId}%2F{pullRequestId}
    tail = url.split("/PullRequestId/")[-1]
    repository_id, _, pull_request_id = tail.replace("%2F", "/").rpartition("/")
    repository_id = repository_id.rpartition("/")[-1]
    return f"{repository_id}:{pull_request_id}"
