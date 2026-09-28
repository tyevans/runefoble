"""Data models for project visualizer graph representation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class GraphNode:
    """Represents an entity node in the visualizer graph."""

    id: str
    label: str
    type: str  # persona, story, prd, task, adr, feature
    color: str = "#8B5CF6"
    status: str = ""
    bc: str = ""
    role: str = ""
    domain: str = ""
    prs: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    x: float = 0.0
    y: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphEdge:
    """Represents a directional relationship between two graph nodes."""

    source_id: str
    target_id: str
    relation: str = "relates_to"
    source_type: str = ""
    target_type: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphData:
    """Collection of graph nodes and connecting edges."""

    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def node_by_id(self, node_id: str) -> GraphNode | None:
        return next((n for n in self.nodes if n.id == node_id), None)

    def edges_for(self, node_id: str) -> list[GraphEdge]:
        return [e for e in self.edges if e.source_id == node_id or e.target_id == node_id]
