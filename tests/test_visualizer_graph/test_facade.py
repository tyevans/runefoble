"""Tests for the visualizer traceability graph builder."""

from __future__ import annotations

from pathlib import Path

from tools.project_visualizer.parser import (
    build_traceability_graph,
    scan_project,
)


def test_traceability_graph_builds_edges_and_metrics(repo_root: Path):
    """Verify scan and build produce a populated traceability graph."""
    scanned_data = scan_project(repo_root)
    built_data = build_traceability_graph(scanned_data)
    assert len(built_data.edges) > 100
    assert built_data.metrics.total_tasks > 0
