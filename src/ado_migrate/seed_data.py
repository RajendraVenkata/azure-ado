from dataclasses import dataclass, field

from ado_migrate.client import Attachment, IterationPath, Link, WorkItem


@dataclass
class CommitPlan:
    message: str
    files: dict[str, str]


@dataclass
class RepoSeedPlan:
    name: str
    commits: list[CommitPlan] = field(default_factory=list)


@dataclass
class SeedPlan:
    area_paths: list[str]
    iteration_paths: list[IterationPath]
    repos: list[RepoSeedPlan]
    work_items: list[WorkItem]


def generate_seed_plan(work_item_count: int = 10) -> SeedPlan:
    area_paths = ["Team A", "Team A/Sub Team"]
    iteration_paths = [
        IterationPath(path="Release 1", start_date="2026-01-01", end_date="2026-03-31"),
        IterationPath(
            path="Release 1/Sprint 1", start_date="2026-01-01", end_date="2026-01-14"
        ),
    ]

    repos = [_generate_repo(f"seed-repo-{i}") for i in range(2)]
    work_items = [_generate_work_item(i) for i in range(work_item_count)]

    if len(work_items) >= 2:
        work_items[0].links.append(Link(link_type="work_item", target=work_items[1].id))

    if work_items and repos:
        work_items[0].links.append(
            Link(link_type="pull_request", target=f"{repos[0].name}:1")
        )

    if work_items:
        work_items[0].attachments.append(
            Attachment(name="repro-steps.txt", content=b"Steps to reproduce...")
        )

    return SeedPlan(
        area_paths=area_paths,
        iteration_paths=iteration_paths,
        repos=repos,
        work_items=work_items,
    )


def _generate_work_item(index: int) -> WorkItem:
    return WorkItem(
        id=f"wi-{index}",
        work_item_type="Bug",
        revisions=[{"Title": f"Seeded work item {index}", "State": "New"}],
    )


def _generate_repo(name: str) -> RepoSeedPlan:
    commits = [
        CommitPlan(
            message=f"Commit {i} to {name}",
            files={"README.md": f"{name} — revision {i}\n"},
        )
        for i in range(4)
    ]
    return RepoSeedPlan(name=name, commits=commits)
