"""Tests for visualizer graph builder, entity parsing, and link validation."""

from __future__ import annotations

from pathlib import Path

from tools.project_visualizer.graph import (
    ProjectGraphBuilder,
    build_graph_data,
    build_graph_edges,
    build_graph_nodes,
)
from tools.project_visualizer.parser import ProjectParser


def test_graph_builder_and_traceability_edges(repo_root: Path):
    """Verify entity parsing and dependency edge construction across documents."""
    parser = ProjectParser(repo_root)
    data = parser.parse_all()
    builder = ProjectGraphBuilder(data)
    builder.build()

    assert len(data.edges) > 100
    relations = {e.relation for e in data.edges}
    assert "desires" in relations
    assert "specifies" in relations
    assert "governed_by" in relations
    assert "deploys_to" in relations


def test_builder_graph_synthesis(repo_root: Path):
    """Verify synthesis of GraphNode and GraphEdge collections from project data."""
    parser = ProjectParser(repo_root)
    data = parser.parse_all()
    builder = ProjectGraphBuilder(data)
    builder.build()

    nodes = build_graph_nodes(data)
    edges = build_graph_edges(data)
    graph = build_graph_data(data)

    assert len(nodes) > 50
    assert len(edges) > 50
    assert len(graph.nodes) == len(nodes)
    assert len(graph.edges) == len(edges)


def test_all_prds_have_stories_and_tasks_support(repo_root: Path):
    """Verify bidirectional link validation ensuring no orphaned stories or unsourced PRDs."""
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
