"""Graph filtering, subgraph extraction, and layout positioning hints."""

from __future__ import annotations

import math
from collections.abc import Sequence

from tools.project_visualizer.graph.models import GraphData, GraphEdge, GraphNode


def filter_graph_nodes(
    nodes: Sequence[GraphNode],
    *,
    hide_done: bool = False,
    active_type: str = "all",
    bc: str = "all",
    search: str = "",
) -> list[GraphNode]:
    """Filter nodes by completion status, entity type, bounded context, and search query."""
    q = search.lower().strip()
    result = []
    for n in nodes:
        if hide_done and n.type == "task" and n.status == "Complete":
            continue
        if active_type != "all" and n.type != active_type:
            continue
        if bc != "all" and n.bc and n.bc != bc:
            continue
        if (
            q
            and q not in n.id.lower()
            and q not in n.label.lower()
            and not any(q in t.lower() for t in n.tags)
        ):
            continue
        result.append(n)
    return result


def filter_graph_edges(
    edges: Sequence[GraphEdge], visible_nodes: Sequence[GraphNode]
) -> list[GraphEdge]:
    """Retain only edges where both source and target nodes are in visible_nodes."""
    node_ids = {n.id for n in visible_nodes}
    return [e for e in edges if e.source_id in node_ids and e.target_id in node_ids]


def filter_graph(
    graph: GraphData,
    *,
    hide_done: bool = False,
    active_type: str = "all",
    bc: str = "all",
    search: str = "",
) -> GraphData:
    """Filter entire graph returning a new GraphData with visible nodes and valid edges."""
    nodes = filter_graph_nodes(
        graph.nodes, hide_done=hide_done, active_type=active_type, bc=bc, search=search
    )
    return GraphData(nodes=nodes, edges=filter_graph_edges(graph.edges, nodes))


def find_subgraph(graph: GraphData, root_id: str, depth: str = "lineage") -> GraphData:
    """Extract connected subgraph starting from root_id."""
    visited: set[str] = {root_id}
    queue: list[str] = [root_id]
    edge_map: dict[str, list[GraphEdge]] = {}
    for e in graph.edges:
        edge_map.setdefault(e.source_id, []).append(e)
        edge_map.setdefault(e.target_id, []).append(e)

    while queue:
        curr = queue.pop(0)
        for e in edge_map.get(curr, []):
            nxt = e.target_id if e.source_id == curr else e.source_id
            if nxt not in visited:
                visited.add(nxt)
                if depth == "lineage":
                    queue.append(nxt)

    nodes = [n for n in graph.nodes if n.id in visited]
    return GraphData(nodes=nodes, edges=filter_graph_edges(graph.edges, nodes))


def apply_layout_hints(
    graph: GraphData, layout: str = "network", width: float = 2200, height: float = 1400
) -> GraphData:
    """Assign initial layout coordinate positioning hints to graph nodes."""
    types = ["persona", "story", "prd", "task", "adr"]
    cx, cy = width / 2.0, height / 2.0
    by_type: dict[str, list[GraphNode]] = {t: [] for t in types}
    for n in graph.nodes:
        by_type.setdefault(n.type, []).append(n)
    if layout == "flow":
        col_w = width / (len(types) + 1)
        for col_idx, t in enumerate(types):
            grp = by_type.get(t, [])
            row_h = height / (len(grp) + 1) if grp else height
            for row_idx, n in enumerate(grp):
                n.x, n.y = round((col_idx + 1) * col_w, 2), round((row_idx + 1) * row_h, 2)
    elif layout == "radial":
        radii = {"persona": 140.0, "story": 280.0, "prd": 420.0, "task": 560.0, "adr": 700.0}
        for t, grp in by_type.items():
            r, count = radii.get(t, 400.0), max(len(grp), 1)
            for i, n in enumerate(grp):
                ang = (2.0 * math.pi * i) / count
                n.x, n.y = round(cx + r * math.cos(ang), 2), round(cy + r * math.sin(ang), 2)
    return graph
