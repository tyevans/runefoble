"""Developer CLI interface for Runefoble Project Visualizer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.project_visualizer.generator import ProjectVisualizerGenerator
from tools.project_visualizer.server import run_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Runefoble Project Content Visualizer CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: serve
    serve_parser = subparsers.add_parser("serve", help="Launch live dynamic visualizer server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    serve_parser.add_argument("--port", type=int, default=8787, help="Port to listen on")
    serve_parser.add_argument("--root", default=".", help="Root repository path")

    # Subcommand: build
    build_parser = subparsers.add_parser("build", help="Generate standalone static HTML bundle")
    build_parser.add_argument(
        "--out",
        default="dist/project-visualizer.html",
        help="Target output HTML file path",
    )
    build_parser.add_argument("--root", default=".", help="Root repository path")

    # Subcommand: stats
    stats_parser = subparsers.add_parser("stats", help="Print project statistics to console")
    stats_parser.add_argument("--root", default=".", help="Root repository path")

    # Subcommand: export-json
    export_parser = subparsers.add_parser("export-json", help="Export project data graph to JSON")
    export_parser.add_argument(
        "--out",
        default="dist/project-data.json",
        help="Target JSON file path",
    )
    export_parser.add_argument("--root", default=".", help="Root repository path")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    generator = ProjectVisualizerGenerator(args.root)

    if args.command == "serve":
        run_server(root_dir=args.root, host=args.host, port=args.port)
        return 0

    elif args.command == "build":
        out_file = generator.build_file(args.out)
        size_kb = round(out_file.stat().st_size / 1024, 1)
        print(f"✅ Generated standalone visualizer: {out_file} ({size_kb} KB)")
        return 0

    elif args.command == "stats":
        data = generator.get_data()
        m = data.metrics
        print("=== Runefoble Project Content Statistics ===")
        print(
            f"Total Backlog Tasks: {m.total_tasks} ({m.completed_tasks} Complete, {m.refined_tasks} Refined, {m.proposed_tasks} Proposed)"
        )
        print(f"Accepted User Stories: {m.total_stories}")
        print(f"Accepted PRDs: {m.total_prds}")
        print(f"Governing ADRs: {m.total_adrs}")
        print(f"Target Personas: {m.total_personas}")
        print(f"Feature Inventory: {m.total_features} ({m.mvp_p0_features} MVP P0)")
        print(f"Traceability Graph Edges: {len(data.edges)}")
        print(
            f"Ready Buffer Health: {m.ready_buffer_status.upper()} ({m.ready_buffer_count} items)"
        )
        if m.tasks_without_adr:
            print(
                f"Tasks without ADRs: {len(m.tasks_without_adr)} ({', '.join(m.tasks_without_adr[:5])}...)"
            )
        return 0

    elif args.command == "export-json":
        data = generator.get_data()
        out = Path(args.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data.to_dict(), indent=2, default=str), encoding="utf-8")
        print(f"✅ Exported project data JSON: {out}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
