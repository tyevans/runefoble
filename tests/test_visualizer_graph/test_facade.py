"""Tests for visualizer graph backward-compatible facades and modular structure."""

from __future__ import annotations

from pathlib import Path

from tools.project_visualizer.parser import (
    build_traceability_graph,
    scan_project,
)
from tools.project_visualizer.parsers import GraphBuilder


def test_graph_builder_facade_compatibility(repo_root: Path):
    """Verify legacy scan_project, build_traceability_graph, and GraphBuilder facades."""
    scanned_data = scan_project(repo_root)
    built_data = build_traceability_graph(scanned_data)
    assert len(built_data.edges) > 100
    assert built_data.metrics.total_tasks > 0

    builder_instance = GraphBuilder(scanned_data)
    assert builder_instance.build() is built_data
