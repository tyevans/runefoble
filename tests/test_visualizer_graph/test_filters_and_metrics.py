"""Tests for visualizer graph filtering, subgraph search, and health metrics."""

from __future__ import annotations

from pathlib import Path

from tools.project_visualizer.graph import (
    GraphData,
    ProjectGraphBuilder,
    build_graph_data,
    filter_graph,
    find_subgraph,
)
from tools.project_visualizer.parser import ProjectParser


def test_health_metrics_calculations(repo_root: Path):
    """Verify health metric calculation assertions and backlog ready buffer status."""
    parser = ProjectParser(repo_root)
    data = parser.parse_all()
    builder = ProjectGraphBuilder(data)
    builder.build()

    m = data.metrics
    assert m.total_adrs >= 13
    assert m.total_prds >= 12
    assert m.total_stories >= 40
    assert m.total_tasks >= 50
    assert m.completed_tasks >= 30
    assert m.refined_tasks >= 0
    assert m.ready_buffer_status in ["optimal", "over_buffered", "under_buffered"]


def test_graph_filtering_and_subgraphs(repo_root: Path):
    """Verify tag/type filtering and search subgraphs extraction."""
    parser = ProjectParser(repo_root)
    data = parser.parse_all()
    builder = ProjectGraphBuilder(data)
    builder.build()
    graph = build_graph_data(data)

    # 1. Filter hide_done
    filtered_done = filter_graph(graph, hide_done=True)
    done_tasks = [n for n in filtered_done.nodes if n.type == "task" and n.status == "Complete"]
    assert len(done_tasks) == 0

    # 2. Filter active_type
    filtered_adr = filter_graph(graph, active_type="adr")
    assert all(n.type == "adr" for n in filtered_adr.nodes)
    assert len(filtered_adr.nodes) > 0

    # 3. Find subgraph by ID and lineage
    first_id = graph.nodes[0].id
    sub = find_subgraph(graph, first_id, depth="lineage")
    assert isinstance(sub, GraphData)
    assert any(n.id == first_id for n in sub.nodes)
