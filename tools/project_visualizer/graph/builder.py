"""Graph construction and traceability linking for project visualizer."""

from __future__ import annotations

from typing import Any

from tools.project_visualizer.graph.linking import (
    link_milestones,
    link_personas,
    link_stories,
    link_tasks,
)
from tools.project_visualizer.graph.metrics import compute_health_metrics
from tools.project_visualizer.graph.models import GraphData, GraphEdge, GraphNode
from tools.project_visualizer.models import ProjectData, TraceabilityEdge

TASK_COLORS = {"Complete": "#10B981", "Refined": "#F59E0B", "Proposed": "#8B5CF6"}


def _node(item: Any, n_type: str, color: str, **kwargs: Any) -> GraphNode:
    label = getattr(item, "title", getattr(item, "name", ""))
    return GraphNode(item.id, label, n_type, color, **kwargs)


def _task_node(t: Any) -> GraphNode:
    return _node(
        t, "task", TASK_COLORS.get(t.status, "#8B5CF6"), status=t.status, bc=t.target_bc, prs=t.prs
    )


def build_graph_nodes(data: ProjectData) -> list[GraphNode]:
    """Construct GraphNode items from project entities."""
    return [
        *[_node(p, "persona", "#F59E0B", role=p.role) for p in data.personas],
        *[_node(s, "story", "#06B6D4", metadata={"persona": s.persona}) for s in data.stories],
        *[_node(p, "prd", "#F43F5E", status=p.status) for p in data.prds],
        *[_task_node(t) for t in data.tasks],
        *[_node(a, "adr", "#6366F1", domain=a.domain) for a in data.adrs],
    ]


def generate_traceability_edges(data: ProjectData) -> None:
    """Synthesize directional traceability edges across project documents."""
    edges: list[TraceabilityEdge] = []
    add = edges.append
    for p in data.personas:
        for s in p.story_ids:
            add(TraceabilityEdge("persona", p.id, "story", s, "desires"))
    for s in data.stories:
        if s.governing_prd:
            add(TraceabilityEdge("story", s.id, "prd", s.governing_prd, "specifies"))
    for prd in data.prds:
        for t in prd.implementing_tasks:
            add(TraceabilityEdge("prd", prd.id, "task", t, "implements"))
    for t in data.tasks:
        for a in t.governing_adrs:
            add(TraceabilityEdge("task", t.id, "adr", a, "governed_by"))
        if t.target_bc:
            add(TraceabilityEdge("task", t.id, "bc", t.target_bc, "deploys_to"))
        for d in t.dependencies:
            dep_id = f"TASK-{d.split('-')[-1].zfill(4)}"
            add(TraceabilityEdge("task", t.id, "task", dep_id, "depends_on"))
    data.edges = edges


def build_graph_edges(data: ProjectData) -> list[GraphEdge]:
    """Synthesize GraphEdge items from project traceability edges."""
    return [
        GraphEdge(e.source_id, e.target_id, e.relation, e.source_type, e.target_type)
        for e in data.edges
    ]


def build_graph_data(data: ProjectData) -> GraphData:
    """Build unified GraphData from ProjectData."""
    return GraphData(nodes=build_graph_nodes(data), edges=build_graph_edges(data))


class ProjectGraphBuilder:
    """Builds relational edges, reverse links, and health metrics."""

    def __init__(self, data: ProjectData):
        self.data = data

    def build(self) -> ProjectData:
        self._link_personas_to_stories()
        self._link_tasks_to_entities()
        self._link_stories_to_prds()
        self._link_features_to_prds()
        self._link_tasks_to_milestones()
        self._generate_traceability_edges()
        self._compute_health_metrics()
        return self.data

    def build_graph_data(self) -> GraphData:
        self.build()
        return build_graph_data(self.data)

    def _link_personas_to_stories(self) -> None:
        link_personas(self.data)

    def _link_tasks_to_entities(self) -> None:
        link_tasks(self.data)

    def _link_stories_to_prds(self) -> None:
        link_stories(self.data)

    def _link_features_to_prds(self) -> None:
        pass

    def _link_tasks_to_milestones(self) -> None:
        link_milestones(self.data)

    def _generate_traceability_edges(self) -> None:
        generate_traceability_edges(self.data)

    def _compute_health_metrics(self) -> None:
        compute_health_metrics(self.data)
