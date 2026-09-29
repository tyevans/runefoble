"""Tests for visualizer graph serialization, layout hints, and HTML bundles."""

from __future__ import annotations

from pathlib import Path

from tools.project_visualizer.generator import ProjectVisualizerGenerator
from tools.project_visualizer.graph import (
    GraphEdge,
    GraphNode,
    ProjectGraphBuilder,
    apply_layout_hints,
    build_graph_data,
)
from tools.project_visualizer.parser import ProjectParser


def test_graph_models_and_dictionary_serialization(repo_root: Path):
    """Verify GraphNode, GraphEdge, and GraphData models and dictionary serialization."""
    parser = ProjectParser(repo_root)
    data = parser.parse_all()
    builder = ProjectGraphBuilder(data)
    builder.build()
    graph = build_graph_data(data)

    node = graph.nodes[0]
    assert isinstance(node, GraphNode)
    node_dict = node.to_dict()
    assert "id" in node_dict and "type" in node_dict and "color" in node_dict

    edge = graph.edges[0]
    assert isinstance(edge, GraphEdge)
    edge_dict = edge.to_dict()
    assert "source_id" in edge_dict and "target_id" in edge_dict and "relation" in edge_dict

    g_dict = graph.to_dict()
    assert "nodes" in g_dict and "edges" in g_dict
    assert graph.node_by_id(node.id) == node


def test_node_positioning_layout_hints(repo_root: Path):
    """Verify flow and radial coordinate generation for node positioning."""
    parser = ProjectParser(repo_root)
    data = parser.parse_all()
    builder = ProjectGraphBuilder(data)
    builder.build()

    flow_g = apply_layout_hints(build_graph_data(data), layout="flow")
    assert any(n.x > 0 and n.y > 0 for n in flow_g.nodes)

    radial_g = apply_layout_hints(build_graph_data(data), layout="radial")
    assert any(n.x > 0 and n.y > 0 for n in radial_g.nodes)


def test_html_bundle_contains_graph_and_gantt(repo_root: Path, tmp_path: Path):
    """Verify generated standalone HTML bundle contains graph and gantt components."""
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
    """Verify mouse focal zoom anchoring and minimap tracking in generated bundle."""
    generator = ProjectVisualizerGenerator(repo_root)
    out_file = tmp_path / "test-zoom-minimap.html"
    result = generator.build_file(out_file)

    content = result.read_text(encoding="utf-8")
    assert "zoomGraph(factor, focalX, focalY)" in content or "zoomGraph" in content
    assert "focalX" in content and "focalY" in content
    assert "mm-node-" in content
    assert "updateMinimap" in content
    assert "moveCameraToMinimapPoint" in content
    assert "minimap-view-rect" in content
    assert "isDraggingMinimap" in content
