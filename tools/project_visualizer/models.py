"""Data models for Runefoble docs/project dynamic content visualizer."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ADRItem:
    id: str
    title: str
    status: str
    date: str
    file_path: str
    context: str = ""
    decision: str = ""
    consequences: str = ""
    domain: str = "Platform"
    raw_markdown: str = ""
    implementing_tasks: list[str] = field(default_factory=list)


@dataclass
class PRDItem:
    id: str
    title: str
    status: str
    created: str
    file_path: str
    target_personas: list[str] = field(default_factory=list)
    problem_statement: str = ""
    outcomes: list[str] = field(default_factory=list)
    raw_markdown: str = ""
    linked_stories: list[str] = field(default_factory=list)
    implementing_tasks: list[str] = field(default_factory=list)


@dataclass
class PersonaItem:
    id: str
    name: str
    role: str
    avatar_color: str
    quote: str = ""
    pain_points: list[str] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)
    key_features: list[str] = field(default_factory=list)
    file_path: str = ""
    story_ids: list[str] = field(default_factory=list)


@dataclass
class UserStoryItem:
    id: str
    title: str
    persona: str
    status: str
    file_path: str
    as_a: str = ""
    i_want: str = ""
    so_that: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)
    raw_markdown: str = ""
    governing_prd: str = ""
    governing_adrs: list[str] = field(default_factory=list)
    implementing_tasks: list[str] = field(default_factory=list)


@dataclass
class CommitInfo:
    hash: str
    author: str
    date: str
    subject: str
    prs: list[str] = field(default_factory=list)


@dataclass
class BacklogTaskItem:
    id: str
    title: str
    status: str  # Complete, Refined, Proposed
    created: str = ""
    completed: str = ""
    file_path: str = ""
    target_bc: str = "platform"
    target_release: str = ""
    dependencies: list[str] = field(default_factory=list)
    governing_adrs: list[str] = field(default_factory=list)
    governing_prds: list[str] = field(default_factory=list)
    governing_stories: list[str] = field(default_factory=list)
    microfrontends: list[str] = field(default_factory=list)
    commits: list[CommitInfo] = field(default_factory=list)
    prs: list[str] = field(default_factory=list)
    summary: str = ""
    milestone: str = ""
    raw_markdown: str = ""


@dataclass
class MilestoneItem:
    id: str
    name: str
    status: str
    description: str = ""
    enablers: list[str] = field(default_factory=list)
    epics: list[str] = field(default_factory=list)
    task_ids: list[str] = field(default_factory=list)
    completion_pct: int = 0


@dataclass
class FeatureItem:
    id: str
    name: str
    domain: str
    tier: str  # P0 (MVP), P1 (Beta), P2 (Horizon)
    description: str
    governing_systems: list[str] = field(default_factory=list)


@dataclass
class TraceabilityEdge:
    source_type: str  # persona, story, prd, task, adr, bc
    source_id: str
    target_type: str
    target_id: str
    relation: str  # desires, specifies, implements, governs, deploys_to


@dataclass
class ProjectHealthMetrics:
    total_adrs: int = 0
    total_prds: int = 0
    total_stories: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    refined_tasks: int = 0
    proposed_tasks: int = 0
    total_features: int = 0
    mvp_p0_features: int = 0
    total_personas: int = 0
    orphaned_stories: list[str] = field(default_factory=list)
    tasks_without_adr: list[str] = field(default_factory=list)
    ready_buffer_status: str = "optimal"  # optimal, under_buffered, over_buffered
    ready_buffer_count: int = 0


@dataclass
class ProjectData:
    adrs: list[ADRItem] = field(default_factory=list)
    prds: list[PRDItem] = field(default_factory=list)
    personas: list[PersonaItem] = field(default_factory=list)
    stories: list[UserStoryItem] = field(default_factory=list)
    tasks: list[BacklogTaskItem] = field(default_factory=list)
    milestones: list[MilestoneItem] = field(default_factory=list)
    features: list[FeatureItem] = field(default_factory=list)
    edges: list[TraceabilityEdge] = field(default_factory=list)
    metrics: ProjectHealthMetrics = field(default_factory=ProjectHealthMetrics)
    data_hash: str = ""
    last_updated: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
