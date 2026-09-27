"""Tests for Project Visualizer graph construction and traceability."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.project_visualizer.generator import ProjectVisualizerGenerator
from tools.project_visualizer.graph import ProjectGraphBuilder
from tools.project_visualizer.parser import (
    ProjectParser,
    build_traceability_graph,
    scan_project,
)
from tools.project_visualizer.parsers import GraphBuilder


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def test_graph_builder_and_traceability_edges(repo_root: Path):
    parser = ProjectParser(repo_root)
    data = parser.parse_all()
    builder = ProjectGraphBuilder(data)
    builder.build()

    assert len(data.edges) > 100

    # Check edge relations
    relations = {e.relation for e in data.edges}
    assert "desires" in relations
    assert "specifies" in relations
    assert "governed_by" in relations
    assert "deploys_to" in relations

    # Check health metrics
    m = data.metrics
    assert m.total_adrs >= 13
    assert m.total_prds >= 12
    assert m.total_stories >= 40
    assert m.total_tasks >= 50
    assert m.completed_tasks >= 30
    assert m.refined_tasks >= 0
    assert m.ready_buffer_status in ["optimal", "over_buffered", "under_buffered"]


def test_graph_builder_facade_compatibility(repo_root: Path):
    scanned_data = scan_project(repo_root)
    built_data = build_traceability_graph(scanned_data)
    assert len(built_data.edges) > 100
    assert built_data.metrics.total_tasks > 0

    builder_instance = GraphBuilder(scanned_data)
    assert builder_instance.build() is built_data


def test_all_prds_have_stories_and_tasks_support(repo_root: Path):
    parser = ProjectParser(repo_root)
    data = parser.parse_all(force=True)
    builder = ProjectGraphBuilder(data)
    builder.build()

    assert len(data.prds) >= 16
    for prd in data.prds:
        assert len(prd.linked_stories) >= 1, f"PRD {prd.id} ({prd.title}) has 0 linked user stories"
        assert len(prd.implementing_tasks) >= 1, (
            f"PRD {prd.id} ({prd.title}) has 0 implementing tasks"
        )

    assert len(data.metrics.orphaned_stories) == 0, (
        f"Found orphaned stories: {data.metrics.orphaned_stories}"
    )


def test_html_bundle_contains_graph_and_gantt(repo_root: Path, tmp_path: Path):
    generator = ProjectVisualizerGenerator(repo_root)
    out_file = tmp_path / "test-full-visualizer.html"
    result = generator.build_file(out_file)

    content = result.read_text(encoding="utf-8")
    assert "Relationship Graph" in content
    assert "Gantt & Timeline" in content
    assert "Hide Done" in content
    assert "Git Commits & Pull Requests" in content
    assert "ForceSimulation" in content
    assert "graph-minimap" in content
    assert "edge-active-flow" in content
    assert "focus-ripple" in content
    assert "switchGraphLayout" in content


def test_graph_visualizer_zoom_and_minimap_bundle(repo_root: Path, tmp_path: Path):
    generator = ProjectVisualizerGenerator(repo_root)
    out_file = tmp_path / "test-zoom-minimap.html"
    result = generator.build_file(out_file)

    content = result.read_text(encoding="utf-8")
    # Verify focal mouse zoom anchoring
    assert "zoomGraph(factor, focalX, focalY)" in content or "zoomGraph" in content
    assert "focalX" in content
    assert "focalY" in content
    # Verify minimap real-time node updates and interaction
    assert "mm-node-" in content
    assert "updateMinimap" in content
    assert "moveCameraToMinimapPoint" in content
    assert "minimap-view-rect" in content
    assert "isDraggingMinimap" in content
