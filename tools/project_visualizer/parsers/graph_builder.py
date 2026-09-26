"""Traceability matrix, dependency linking, and graph model builder."""

from __future__ import annotations

from tools.project_visualizer.graph import ProjectGraphBuilder
from tools.project_visualizer.models import ProjectData


def build_traceability_graph(data: ProjectData) -> ProjectData:
    """Build relational edges, reverse links, and health metrics for project data."""
    return ProjectGraphBuilder(data).build()


GraphBuilder = ProjectGraphBuilder

__all__ = [
    "GraphBuilder",
    "ProjectGraphBuilder",
    "build_traceability_graph",
]
