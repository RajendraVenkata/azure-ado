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
from azure.devops.v7_1.git.models import GitRepositoryCreateOptions
from azure.devops.v7_1.work_item_tracking.models import (
    JsonPatchOperation,
    TeamContext,
    Wiql,
    WorkItemClassificationNode,
)
from msrest.authentication import BasicAuthentication

from ado_migrate.client import AdoClient, Attachment, IterationPath, Link, Repo, WorkItem
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
_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
_STATUS_CODE_IN_MESSAGE = re.compile(r"returned a (\d+) status code")


class RealAdoClient(AdoClient):
    def __init__(self, organization_url: str, pat: str, dry_run: bool = False):
        super().__init__(dry_run)
        connection = Connection(
            base_url=organization_url, creds=BasicAuthentication("", pat)
        )
        self._wit_client = connection.get_client(_WIT_CLIENT_PATH)
        self._git_client = connection.get_client(_GIT_CLIENT_PATH)
        self._core_client = connection.get_client(_CORE_CLIENT_PATH)
        self._organization_url = organization_url.rstrip("/")
        self._project_id_cache: dict[str, str] = {}

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
        result = self._call(
            self._wit_client.query_by_wiql,
            Wiql(query="SELECT [System.Id] FROM WorkItems"),
            team_context=TeamContext(project=project),
        )
        return [
            self.get_work_item(project, str(item.id)) for item in (result.work_items or [])
        ]

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
    return {_FRIENDLY_FIELD_NAMES.get(k, k): v for k, v in (fields or {}).items()}


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
