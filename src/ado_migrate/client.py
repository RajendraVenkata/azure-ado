from dataclasses import dataclass, field
from typing import Any, Optional

from ado_migrate.mutation import DryRunGuard


@dataclass(frozen=True)
class IterationPath:
    path: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@dataclass
class Attachment:
    name: str
    content: bytes


@dataclass(frozen=True)
class ReleasePipeline:
    id: str
    name: str


@dataclass
class Dashboard:
    id: str
    name: str
    widgets: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ArtifactFeed:
    id: str
    name: str


@dataclass(frozen=True)
class Extension:
    id: str
    name: str


@dataclass
class Repo:
    id: str
    name: str
    clone_url: str


@dataclass(frozen=True)
class Link:
    link_type: str
    target: str


@dataclass
class ServiceConnection:
    id: str
    name: str
    connection_type: str
    config: dict[str, Any] = field(default_factory=dict)
    has_secret: bool = False


@dataclass
class Query:
    id: str
    name: str
    folder_path: str
    wiql: str


@dataclass
class SecurityGroup:
    id: str
    name: str
    member_identities: list[str] = field(default_factory=list)


@dataclass
class TestSuite:
    id: str
    name: str
    parent_suite_id: Optional[str] = None
    test_case_ids: list[str] = field(default_factory=list)
    configuration_names: list[str] = field(default_factory=list)


@dataclass
class TestPlan:
    id: str
    name: str
    suites: list[TestSuite] = field(default_factory=list)


@dataclass
class Pipeline:
    id: str
    name: str
    yaml_path: str
    repo_id: str
    service_connection_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Team:
    id: str
    name: str


@dataclass(frozen=True)
class TeamAreaPath:
    path: str
    include_children: bool = False


@dataclass
class WorkItem:
    id: str
    work_item_type: str
    revisions: list[dict[str, Any]]
    attachments: list[Attachment] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)


class AdoClient(DryRunGuard):
    """Base for real (SDK/REST-backed) and fake AdoClient implementations.

    Concrete artifact-type operations (create_repo, create_work_item, ...)
    are added here incrementally by later tickets.
    """


class InMemoryFakeAdoClient(AdoClient):
    def __init__(self, dry_run: bool = False):
        super().__init__(dry_run)
        self.created: list[str] = []
        self._area_paths: dict[str, list[str]] = {}
        self._iteration_paths: dict[str, list[IterationPath]] = {}
        self._work_items: dict[str, list[WorkItem]] = {}
        self._destination_work_items: dict[str, WorkItem] = {}
        self._next_work_item_id = 1
        self._repos: dict[str, list[Repo]] = {}
        self._next_repo_id = 1
        self._wikis: dict[str, list[Repo]] = {}
        self._next_wiki_id = 1
        self._service_connections: dict[str, list[ServiceConnection]] = {}
        self._next_service_connection_id = 1
        self._pipelines: dict[str, list[Pipeline]] = {}
        self._next_pipeline_id = 1
        self._queries: dict[str, list[Query]] = {}
        self._next_query_id = 1
        self._test_plans: dict[str, list[TestPlan]] = {}
        self._next_test_plan_id = 1
        self._next_test_suite_id = 1
        self._security_groups: dict[str, list[SecurityGroup]] = {}
        self._next_security_group_id = 1
        self._release_pipelines: dict[str, list[ReleasePipeline]] = {}
        self._dashboards: dict[str, list[Dashboard]] = {}
        self._artifact_feeds: dict[str, list[ArtifactFeed]] = {}
        self._used_extensions: dict[str, list[Extension]] = {}
        self._project_users: dict[str, list[str]] = {}
        self._teams: dict[str, list[Team]] = {}
        self._next_team_id = 1
        self._team_iterations: dict[tuple[str, str], list[str]] = {}
        self._team_area_paths: dict[tuple[str, str], list[TeamAreaPath]] = {}

    def create_placeholder(self, name: str) -> Optional[str]:
        def do_create() -> str:
            destination_id = f"dest-{name}"
            self.created.append(destination_id)
            return destination_id

        return self._mutate(f"create placeholder '{name}'", do_create)

    def seed_area_paths(self, project: str, paths: list[str]) -> None:
        bucket = self._area_paths.setdefault(project, [])
        for path in paths:
            if path not in bucket:
                bucket.append(path)

    def list_area_paths(self, project: str) -> list[str]:
        return list(self._area_paths.get(project, []))

    def create_area_path(self, project: str, path: str) -> Optional[str]:
        def do_create() -> str:
            bucket = self._area_paths.setdefault(project, [])
            if path not in bucket:
                bucket.append(path)
            return path

        return self._mutate(f"create area path '{path}' in {project}", do_create)

    def seed_iteration_paths(self, project: str, paths: list[IterationPath]) -> None:
        bucket = self._iteration_paths.setdefault(project, [])
        existing = {p.path for p in bucket}
        for path in paths:
            if path.path not in existing:
                bucket.append(path)

    def list_iteration_paths(self, project: str) -> list[IterationPath]:
        return list(self._iteration_paths.get(project, []))

    def create_iteration_path(
        self,
        project: str,
        path: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[str]:
        def do_create() -> str:
            bucket = self._iteration_paths.setdefault(project, [])
            if not any(p.path == path for p in bucket):
                bucket.append(IterationPath(path, start_date, end_date))
            return path

        return self._mutate(f"create iteration path '{path}' in {project}", do_create)

    def seed_project_users(self, project: str, users: list[str]) -> None:
        self._project_users.setdefault(project, []).extend(users)

    def list_project_users(self, project: str) -> list[str]:
        return list(self._project_users.get(project, []))

    def seed_work_items(self, project: str, work_items: list[WorkItem]) -> None:
        self._work_items.setdefault(project, []).extend(work_items)

    def list_work_items(self, project: str) -> list[WorkItem]:
        return list(self._work_items.get(project, []))

    def create_work_item(
        self, project: str, work_item_type: str, fields: dict[str, Any]
    ) -> Optional[str]:
        def do_create() -> str:
            destination_id = f"wi-{self._next_work_item_id}"
            self._next_work_item_id += 1
            self._destination_work_items[destination_id] = WorkItem(
                id=destination_id,
                work_item_type=work_item_type,
                revisions=[dict(fields)],
            )
            return destination_id

        return self._mutate(f"create {work_item_type} in {project}", do_create)

    def update_work_item_fields(
        self, project: str, destination_id: str, fields: dict[str, Any]
    ) -> None:
        def do_update() -> None:
            self._destination_work_items[destination_id].revisions.append(dict(fields))

        self._mutate(f"update work item {destination_id} in {project}", do_update)

    def add_attachment(
        self, project: str, destination_id: str, attachment: Attachment
    ) -> None:
        def do_add() -> None:
            self._destination_work_items[destination_id].attachments.append(attachment)

        self._mutate(
            f"add attachment '{attachment.name}' to work item {destination_id} in {project}",
            do_add,
        )

    def update_work_item_links(
        self, project: str, destination_id: str, links: list[Link]
    ) -> None:
        def do_update() -> None:
            self._destination_work_items[destination_id].links = list(links)

        self._mutate(f"update links on work item {destination_id} in {project}", do_update)

    def get_work_item(self, project: str, destination_id: str) -> WorkItem:
        return self._destination_work_items[destination_id]

    def seed_repos(self, project: str, repos: list[Repo]) -> None:
        self._repos.setdefault(project, []).extend(repos)

    def list_repos(self, project: str) -> list[Repo]:
        return list(self._repos.get(project, []))

    def create_repo(self, project: str, name: str) -> Optional[Repo]:
        def do_create() -> Repo:
            destination_id = f"repo-{self._next_repo_id}"
            self._next_repo_id += 1
            repo = Repo(
                id=destination_id,
                name=name,
                clone_url=f"https://dest/{project}/{name}.git",
            )
            self._repos.setdefault(project, []).append(repo)
            return repo

        return self._mutate(f"create repo '{name}' in {project}", do_create)

    def seed_wikis(self, project: str, wikis: list[Repo]) -> None:
        self._wikis.setdefault(project, []).extend(wikis)

    def list_wikis(self, project: str) -> list[Repo]:
        return list(self._wikis.get(project, []))

    def create_wiki(self, project: str, name: str) -> Optional[Repo]:
        def do_create() -> Repo:
            destination_id = f"wiki-{self._next_wiki_id}"
            self._next_wiki_id += 1
            wiki = Repo(
                id=destination_id,
                name=name,
                clone_url=f"https://dest/{project}/{name}",
            )
            self._wikis.setdefault(project, []).append(wiki)
            return wiki

        return self._mutate(f"create wiki '{name}' in {project}", do_create)

    def seed_service_connections(
        self, project: str, connections: list[ServiceConnection]
    ) -> None:
        self._service_connections.setdefault(project, []).extend(connections)

    def list_service_connections(self, project: str) -> list[ServiceConnection]:
        return list(self._service_connections.get(project, []))

    def create_service_connection(
        self,
        project: str,
        name: str,
        connection_type: str,
        config: dict[str, Any],
        has_secret: bool = False,
    ) -> Optional[ServiceConnection]:
        def do_create() -> ServiceConnection:
            destination_id = f"sc-{self._next_service_connection_id}"
            self._next_service_connection_id += 1
            connection = ServiceConnection(
                id=destination_id,
                name=name,
                connection_type=connection_type,
                config=dict(config),
                has_secret=has_secret,
            )
            self._service_connections.setdefault(project, []).append(connection)
            return connection

        return self._mutate(
            f"create service connection '{name}' in {project}", do_create
        )

    def seed_pipelines(self, project: str, pipelines: list[Pipeline]) -> None:
        self._pipelines.setdefault(project, []).extend(pipelines)

    def list_pipelines(self, project: str) -> list[Pipeline]:
        return list(self._pipelines.get(project, []))

    def create_pipeline(
        self,
        project: str,
        name: str,
        yaml_path: str,
        repo_id: str,
        service_connection_ids: list[str],
    ) -> Optional[Pipeline]:
        def do_create() -> Pipeline:
            destination_id = f"pl-{self._next_pipeline_id}"
            self._next_pipeline_id += 1
            pipeline = Pipeline(
                id=destination_id,
                name=name,
                yaml_path=yaml_path,
                repo_id=repo_id,
                service_connection_ids=list(service_connection_ids),
            )
            self._pipelines.setdefault(project, []).append(pipeline)
            return pipeline

        return self._mutate(f"create pipeline '{name}' in {project}", do_create)

    def seed_queries(self, project: str, queries: list[Query]) -> None:
        self._queries.setdefault(project, []).extend(queries)

    def list_queries(self, project: str) -> list[Query]:
        return list(self._queries.get(project, []))

    def create_query(
        self, project: str, name: str, folder_path: str, wiql: str
    ) -> Optional[Query]:
        def do_create() -> Query:
            destination_id = f"q-{self._next_query_id}"
            self._next_query_id += 1
            query = Query(
                id=destination_id, name=name, folder_path=folder_path, wiql=wiql
            )
            self._queries.setdefault(project, []).append(query)
            return query

        return self._mutate(f"create query '{name}' in {project}", do_create)

    def seed_test_plans(self, project: str, plans: list[TestPlan]) -> None:
        self._test_plans.setdefault(project, []).extend(plans)

    def list_test_plans(self, project: str) -> list[TestPlan]:
        return list(self._test_plans.get(project, []))

    def create_test_plan(self, project: str, name: str) -> Optional[TestPlan]:
        def do_create() -> TestPlan:
            destination_id = f"tp-{self._next_test_plan_id}"
            self._next_test_plan_id += 1
            plan = TestPlan(id=destination_id, name=name, suites=[])
            self._test_plans.setdefault(project, []).append(plan)
            return plan

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
            destination_id = f"ts-{self._next_test_suite_id}"
            self._next_test_suite_id += 1
            suite = TestSuite(
                id=destination_id,
                name=name,
                parent_suite_id=parent_suite_id,
                test_case_ids=list(test_case_ids),
                configuration_names=list(configuration_names),
            )
            self.get_test_plan(project, plan_id).suites.append(suite)
            return suite

        return self._mutate(f"create test suite '{name}' in {project}", do_create)

    def get_test_plan(self, project: str, destination_id: str) -> TestPlan:
        return next(
            plan
            for plan in self._test_plans.get(project, [])
            if plan.id == destination_id
        )

    def seed_security_groups(self, project: str, groups: list[SecurityGroup]) -> None:
        self._security_groups.setdefault(project, []).extend(groups)

    def list_security_groups(self, project: str) -> list[SecurityGroup]:
        return list(self._security_groups.get(project, []))

    def create_security_group(
        self, project: str, name: str, member_identities: list[str]
    ) -> Optional[SecurityGroup]:
        def do_create() -> SecurityGroup:
            destination_id = f"sg-{self._next_security_group_id}"
            self._next_security_group_id += 1
            group = SecurityGroup(
                id=destination_id,
                name=name,
                member_identities=list(member_identities),
            )
            self._security_groups.setdefault(project, []).append(group)
            return group

        return self._mutate(f"create security group '{name}' in {project}", do_create)

    def seed_release_pipelines(
        self, project: str, pipelines: list[ReleasePipeline]
    ) -> None:
        self._release_pipelines.setdefault(project, []).extend(pipelines)

    def list_release_pipelines(self, project: str) -> list[ReleasePipeline]:
        return list(self._release_pipelines.get(project, []))

    def seed_dashboards(self, project: str, dashboards: list[Dashboard]) -> None:
        self._dashboards.setdefault(project, []).extend(dashboards)

    def list_dashboards(self, project: str) -> list[Dashboard]:
        return list(self._dashboards.get(project, []))

    def seed_artifact_feeds(self, project: str, feeds: list[ArtifactFeed]) -> None:
        self._artifact_feeds.setdefault(project, []).extend(feeds)

    def list_artifact_feeds(self, project: str) -> list[ArtifactFeed]:
        return list(self._artifact_feeds.get(project, []))

    def seed_used_extensions(self, project: str, extensions: list[Extension]) -> None:
        self._used_extensions.setdefault(project, []).extend(extensions)

    def list_used_extensions(self, project: str) -> list[Extension]:
        return list(self._used_extensions.get(project, []))

    def seed_teams(self, project: str, teams: list[Team]) -> None:
        self._teams.setdefault(project, []).extend(teams)

    def list_teams(self, project: str) -> list[Team]:
        return list(self._teams.get(project, []))

    def create_team(self, project: str, name: str) -> Optional[Team]:
        def do_create() -> Team:
            destination_id = f"team-{self._next_team_id}"
            self._next_team_id += 1
            team = Team(id=destination_id, name=name)
            self._teams.setdefault(project, []).append(team)
            return team

        return self._mutate(f"create team '{name}' in {project}", do_create)

    def seed_team_iterations(self, project: str, team: str, paths: list[str]) -> None:
        self._team_iterations.setdefault((project, team), []).extend(paths)

    def list_team_iterations(self, project: str, team: str) -> list[str]:
        return list(self._team_iterations.get((project, team), []))

    def add_team_iteration(self, project: str, team: str, path: str) -> None:
        def do_add() -> None:
            bucket = self._team_iterations.setdefault((project, team), [])
            if path not in bucket:
                bucket.append(path)

        self._mutate(f"add iteration '{path}' to team '{team}' in {project}", do_add)

    def seed_team_area_paths(
        self, project: str, team: str, area_paths: list[TeamAreaPath]
    ) -> None:
        self._team_area_paths.setdefault((project, team), []).extend(area_paths)

    def list_team_area_paths(self, project: str, team: str) -> list[TeamAreaPath]:
        return list(self._team_area_paths.get((project, team), []))

    def set_team_area_paths(
        self, project: str, team: str, area_paths: list[TeamAreaPath]
    ) -> None:
        def do_set() -> None:
            self._team_area_paths[(project, team)] = list(area_paths)

        self._mutate(f"set area paths for team '{team}' in {project}", do_set)
