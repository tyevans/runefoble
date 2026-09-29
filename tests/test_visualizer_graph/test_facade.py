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


def test_python_graph_modular_decomposition_and_line_invariants(repo_root: Path):
    """Verify TASK-0227 decomposition: submodules exist, strictly < 130 lines, facade < 40 lines."""
    graph_py = repo_root / "tools" / "project_visualizer" / "graph.py"
    graph_dir = repo_root / "tools" / "project_visualizer" / "graph"

    assert graph_py.exists(), "graph.py facade must exist"
    assert graph_dir.is_dir(), "graph/ submodule directory must exist"

    # Facade line check (< 40 lines per DoD)
    facade_lines = len(graph_py.read_text(encoding="utf-8").splitlines())
    assert facade_lines < 40, f"graph.py facade has {facade_lines} lines (must be < 40)"

    # Specific targets from TASK-0227 specification
    targets = {
        "models.py": 90,
        "builder.py": 120,
        "filtering.py": 110,
    }

    for filename, max_lines in targets.items():
        module_file = graph_dir / filename
        assert module_file.exists(), f"Submodule {filename} must exist under graph/"
        lines = len(module_file.read_text(encoding="utf-8").splitlines())
        assert lines < max_lines, f"{filename} has {lines} lines, exceeding target < {max_lines}"
        assert lines < 130, f"{filename} has {lines} lines, violating DoD 2 limit (< 130)"

    # DoD 2 Invariant: Every Python submodule under graph/ is strictly < 130 lines
    for f in graph_dir.glob("*.py"):
        lines = len(f.read_text(encoding="utf-8").splitlines())
        assert lines < 130, f"File {f.name} in graph/ exceeds 130 lines ({lines})"
