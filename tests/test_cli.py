from ado_migrate.cli import parse_args, run
from ado_migrate.client import InMemoryFakeAdoClient, Repo
from ado_migrate.git_transport import InMemoryFakeGitTransport


def _write_config(tmp_path, monkeypatch):
    monkeypatch.setenv("SOURCE_PAT", "s")
    monkeypatch.setenv("DEST_PAT", "d")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
        source:
          organization_url: https://dev.azure.com/source-org
          project: MyProject
          pat_env: SOURCE_PAT
        destination:
          organization_url: https://dev.azure.com/dest-org
          project: MyProject
          pat_env: DEST_PAT
        """
    )
    return config_path


def test_dry_run_produces_report_and_makes_no_mutating_calls(tmp_path, monkeypatch):
    config_path = _write_config(tmp_path, monkeypatch)
    source_client = InMemoryFakeAdoClient(dry_run=False)
    dest_client = InMemoryFakeAdoClient(dry_run=True)
    git_transport = InMemoryFakeGitTransport(dry_run=True)

    args = parse_args(["--config", str(config_path), "--dry-run"])
    exit_code = run(args, source_client, dest_client, git_transport)

    assert exit_code == 0
    report_path = tmp_path / "report.html"
    assert report_path.exists()
    assert "Dry Run" in report_path.read_text()
    assert dest_client.mutation_log == []
    assert git_transport.mutation_log == []


def test_real_run_twice_is_idempotent(tmp_path, monkeypatch):
    config_path = _write_config(tmp_path, monkeypatch)
    source_client = InMemoryFakeAdoClient(dry_run=False)
    dest_client = InMemoryFakeAdoClient(dry_run=False)
    git_transport = InMemoryFakeGitTransport(dry_run=False)

    args = parse_args(["--config", str(config_path)])
    first_exit = run(args, source_client, dest_client, git_transport)

    state_path = tmp_path / "state.json"
    first_state = state_path.read_text()

    second_exit = run(args, source_client, dest_client, git_transport)
    second_state = state_path.read_text()

    assert first_exit == 0
    assert second_exit == 0
    assert first_state == second_state


def test_only_flag_restricts_run_to_specified_types(tmp_path, monkeypatch):
    config_path = _write_config(tmp_path, monkeypatch)
    source_client = InMemoryFakeAdoClient(dry_run=False)
    dest_client = InMemoryFakeAdoClient(dry_run=False)
    git_transport = InMemoryFakeGitTransport(dry_run=False)
    source_client.seed_repos(
        "MyProject",
        [Repo(id="repo-1", name="my-repo", clone_url="https://source/my-repo.git")],
    )

    args = parse_args(["--config", str(config_path), "--only", "repos"])
    run(args, source_client, dest_client, git_transport)

    report_html = (tmp_path / "report.html").read_text()
    assert "Repositories" in report_html
    assert "Work Items" not in report_html
