"""Command line entrypoint for the autonomous backlog execution engine."""

import argparse
import sys
from pathlib import Path

from .orchestrator import run_orchestrator


def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous Backlog Execution Engine")
    parser.add_argument(
        "--drain",
        action="store_true",
        help="Continuously drain the queue until no unblocked ready tasks remain",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of concurrent worker streams (default: 1)",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use local git merge instead of opening and watching GitHub PRs",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect queue and list next unblocked ready tasks without executing",
    )
    parser.add_argument(
        "--repo-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root directory",
    )

    args = parser.parse_args()

    exit_code = run_orchestrator(
        repo_root=args.repo_dir,
        drain=args.drain,
        concurrency=args.concurrency,
        local_mode=args.local,
        dry_run=args.dry_run,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
