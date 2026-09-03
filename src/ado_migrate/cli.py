import argparse
import os
import sys
from argparse import Namespace

from ado_migrate.client import AdoClient
from ado_migrate.config import load_config
from ado_migrate.git_transport import GitTransport
from ado_migrate.report import ReportData, render_report
from ado_migrate.state import StateStore


def parse_args(argv: list[str]) -> Namespace:
    parser = argparse.ArgumentParser(prog="migrate")
    parser.add_argument("--config", required=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def run(args: Namespace, ado_client: AdoClient, git_transport: GitTransport) -> int:
    load_config(args.config)  # validates config + resolves PATs before proceeding

    config_dir = os.path.dirname(os.path.abspath(args.config))
    state = StateStore(os.path.join(config_dir, "state.json"))
    state.load()

    # No artifact-type migrators are wired in yet (added by later tickets).

    report_data = ReportData(dry_run=args.dry_run, sections=[])
    with open(os.path.join(config_dir, "report.html"), "w") as f:
        f.write(render_report(report_data))

    state.save()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    ado_client = AdoClient(dry_run=args.dry_run)
    git_transport = GitTransport(dry_run=args.dry_run)
    return run(args, ado_client, git_transport)


if __name__ == "__main__":
    sys.exit(main())
