import argparse
import logging
import os
import sys
from argparse import Namespace

from ado_migrate.client import AdoClient
from ado_migrate.config import load_config
from ado_migrate.git_transport import GitTransport
from ado_migrate.identity import IdentityMap, load_identity_map
from ado_migrate.orchestrator import run_migration
from ado_migrate.report import render_report
from ado_migrate.state import StateStore


def parse_args(argv: list[str]) -> Namespace:
    parser = argparse.ArgumentParser(prog="migrate")
    parser.add_argument("--config", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--identity-map")
    parser.add_argument("--only")
    return parser.parse_args(argv)


def run(
    args: Namespace,
    source_client: AdoClient,
    dest_client: AdoClient,
    git_transport: GitTransport,
) -> int:
    config = load_config(args.config)  # validates config + resolves PATs
    identity_map = (
        load_identity_map(args.identity_map) if args.identity_map else IdentityMap({})
    )
    only = set(args.only.split(",")) if args.only else None

    config_dir = os.path.dirname(os.path.abspath(args.config))
    state = StateStore(os.path.join(config_dir, "state.json"))
    state.load()

    report_data = run_migration(
        source_client,
        dest_client,
        git_transport,
        config.source.project,
        config.destination.project,
        state,
        identity_map,
        only=only,
    )

    with open(os.path.join(config_dir, "report.html"), "w") as f:
        f.write(render_report(report_data))

    state.save()
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args(argv if argv is not None else sys.argv[1:])
    source_client = AdoClient(dry_run=False)
    dest_client = AdoClient(dry_run=args.dry_run)
    git_transport = GitTransport(dry_run=args.dry_run)
    return run(args, source_client, dest_client, git_transport)


if __name__ == "__main__":
    sys.exit(main())
