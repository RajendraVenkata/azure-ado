"""seed-ado: populate a real Azure DevOps org with test data.

Project creation and the full seeding walk (`create_project`, `seed_project`,
`main`) are deliberately excluded from the automated test suite (see spec
ado-real-client-seeder, ticket 06) — they make real HTTP/git calls.
`parse_args` and `render_seeded_config` are pure and are unit tested.
"""

import argparse
import logging
import os
import subprocess
import sys
import tempfile
import time
from argparse import Namespace
from base64 import b64encode
from datetime import datetime, timezone
from typing import Optional

from azure.devops.connection import Connection
from azure.devops.v7_1.core.models import TeamProject
from msrest.authentication import BasicAuthentication

from ado_migrate.client import Link
from ado_migrate.real_client import RealAdoClient
from ado_migrate.real_git_transport import RealGitTransport
from ado_migrate.seed_data import RepoSeedPlan, SeedPlan, generate_seed_plan

logger = logging.getLogger(__name__)

_PLACEHOLDER = "CHANGE_ME"
_CORE_CLIENT_PATH = "azure.devops.v7_1.core.core_client.CoreClient"
_OPERATIONS_CLIENT_PATH = "azure.devops.v7_1.operations.operations_client.OperationsClient"
_PROCESS_CLIENT_PATH = (
    "azure.devops.v7_1.work_item_tracking_process."
    "work_item_tracking_process_client.WorkItemTrackingProcessClient"
)
_PREFERRED_PROCESS_NAMES = ("Agile", "Scrum", "CMMI", "Basic")


def parse_args(argv: list[str]) -> Namespace:
    parser = argparse.ArgumentParser(prog="seed-ado")
    parser.add_argument("--org", required=True)
    parser.add_argument("--pat-env", required=True)
    parser.add_argument("--project-prefix", required=True)
    parser.add_argument("--work-item-count", type=int, default=10)
    return parser.parse_args(argv)


def render_seeded_config(organization_url: str, project_name: str, pat_env: str) -> str:
    return (
        "source:\n"
        f"  organization_url: {organization_url}\n"
        f"  project: {project_name}\n"
        f"  pat_env: {pat_env}\n"
        "destination:\n"
        f"  organization_url: {_PLACEHOLDER}"
        "  # TODO: fill in your destination org before running migrate\n"
        f"  project: {_PLACEHOLDER}"
        "  # TODO: fill in your destination project\n"
        f"  pat_env: {_PLACEHOLDER}"
        "  # TODO: fill in your destination PAT env var name\n"
    )


class ProjectCreationError(Exception):
    pass


def create_project(
    organization_url: str, pat: str, name: str, timeout_seconds: int = 600
) -> None:
    connection = Connection(base_url=organization_url, creds=BasicAuthentication("", pat))
    core_client = connection.get_client(_CORE_CLIENT_PATH)
    process_client = connection.get_client(_PROCESS_CLIENT_PATH)
    operations_client = connection.get_client(_OPERATIONS_CLIENT_PATH)

    processes = process_client.get_list_of_processes()
    process = next(
        (
            p
            for preferred in _PREFERRED_PROCESS_NAMES
            for p in processes
            if p.name == preferred
        ),
        None,
    )
    if process is None:
        raise ProjectCreationError(
            f"None of the expected process templates {_PREFERRED_PROCESS_NAMES} "
            f"were found in this organization"
        )

    logger.info("Creating project '%s' (process: %s)", name, process.name)
    operation = core_client.queue_create_project(
        TeamProject(
            name=name,
            description="Seeded by ado-migrate seed-ado for migration testing.",
            capabilities={
                "versioncontrol": {"sourceControlType": "Git"},
                "processTemplate": {"templateTypeId": process.type_id},
            },
        )
    )

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        status = operations_client.get_operation(operation.id)
        if status.status == "succeeded":
            logger.info("Project '%s' created", name)
            return
        if status.status in ("failed", "cancelled"):
            raise ProjectCreationError(
                f"Project creation {status.status}: "
                f"{status.detailed_message or status.result_message}"
            )
        time.sleep(3)

    raise ProjectCreationError(
        f"Timed out after {timeout_seconds}s waiting for project '{name}' to be created"
    )


def seed_project(
    real_client: RealAdoClient,
    git_transport: RealGitTransport,
    pat: str,
    project: str,
    plan: SeedPlan,
) -> None:
    logger.info("Seeding area paths")
    for path in sorted(plan.area_paths, key=lambda p: p.count("/")):
        real_client.create_area_path(project, path)

    logger.info("Seeding iteration paths")
    for iteration in sorted(plan.iteration_paths, key=lambda i: i.path.count("/")):
        real_client.create_iteration_path(
            project, iteration.path, iteration.start_date, iteration.end_date
        )

    logger.info("Seeding %d repositories", len(plan.repos))
    repo_id_by_name: dict[str, str] = {}
    for repo_plan in plan.repos:
        repo = real_client.create_repo(project, repo_plan.name)
        _push_seeded_commits(git_transport, pat, repo_plan, repo.clone_url)
        repo_id_by_name[repo_plan.name] = repo.id

    logger.info("Seeding %d work items", len(plan.work_items))
    destination_id_by_plan_id: dict[str, str] = {}
    for wi_plan in plan.work_items:
        first_fields, *later_revisions = wi_plan.revisions
        destination_id = real_client.create_work_item(
            project, wi_plan.work_item_type, first_fields
        )
        for fields in later_revisions:
            real_client.update_work_item_fields(project, destination_id, fields)
        for attachment in wi_plan.attachments:
            real_client.add_attachment(project, destination_id, attachment)
        destination_id_by_plan_id[wi_plan.id] = destination_id

    logger.info("Wiring up work item links")
    for wi_plan in plan.work_items:
        if not wi_plan.links:
            continue
        resolved_links = [
            _resolve_link(link, destination_id_by_plan_id, repo_id_by_name)
            for link in wi_plan.links
        ]
        real_client.update_work_item_links(
            project, destination_id_by_plan_id[wi_plan.id], resolved_links
        )


def _resolve_link(
    link: Link, destination_id_by_plan_id: dict[str, str], repo_id_by_name: dict[str, str]
) -> Link:
    if link.link_type == "work_item":
        return Link(link_type="work_item", target=destination_id_by_plan_id[link.target])
    if link.link_type == "pull_request":
        repo_name, _, pr_number = link.target.partition(":")
        return Link(link_type="pull_request", target=f"{repo_id_by_name[repo_name]}:{pr_number}")
    raise ValueError(f"Unknown link type: {link.link_type}")


def _push_seeded_commits(
    git_transport: RealGitTransport,
    pat: str,
    repo_plan: RepoSeedPlan,
    destination_url: str,
) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        _run_git(["init", "--initial-branch=main", tmp_dir], pat)
        for commit in repo_plan.commits:
            for file_name, content in commit.files.items():
                file_path = os.path.join(tmp_dir, file_name)
                os.makedirs(os.path.dirname(file_path) or tmp_dir, exist_ok=True)
                with open(file_path, "w") as f:
                    f.write(content)
            _run_git(["-C", tmp_dir, "add", "-A"], pat)
            _run_git(["-C", tmp_dir, "commit", "-m", commit.message], pat)
        _run_git(["-C", tmp_dir, "push", destination_url, "main"], pat)


def _run_git(args: list[str], pat: str) -> None:
    auth_header = f"Authorization: Basic {b64encode(f':{pat}'.encode()).decode()}"
    command = [
        "git",
        "-c",
        f"http.extraHeader={auth_header}",
        "-c",
        "user.name=ado-migrate-seeder",
        "-c",
        "user.email=ado-migrate-seeder@example.com",
        *args,
    ]
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=300)


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args(argv if argv is not None else sys.argv[1:])

    pat = os.environ.get(args.pat_env)
    if pat is None:
        print(f"Environment variable '{args.pat_env}' is not set", file=sys.stderr)
        return 1

    project_name = f"{args.project_prefix}-{datetime.now(timezone.utc):%Y%m%d%H%M%S}"

    try:
        create_project(args.org, pat, project_name)

        real_client = RealAdoClient(args.org, pat, dry_run=False)
        git_transport = RealGitTransport(pat, pat, dry_run=False)
        plan = generate_seed_plan(work_item_count=args.work_item_count)
        seed_project(real_client, git_transport, pat, project_name, plan)
    except Exception as exc:
        print(f"seed-ado failed: {exc}", file=sys.stderr)
        return 1

    config_path = "seeded-config.yaml"
    with open(config_path, "w") as f:
        f.write(render_seeded_config(args.org, project_name, args.pat_env))

    logger.info("Done. Wrote %s — fill in the destination section before running migrate.", config_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
