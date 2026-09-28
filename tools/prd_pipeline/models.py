"""Domain models and data structures for PRD pipeline and task decomposition."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .manager.models import PRD, PRDRecord, PRDStage


class PRDStatus(StrEnum):
    IDEA = "Idea"
    SHAPED = "Shaped"
    ACCEPTED = "Accepted"
    SHIPPED = "Shipped"


class SliceType(StrEnum):
    SPIKE = "spike"
    DOMAIN_AGGREGATE = "domain_aggregate"
    API_AUTH = "api_auth"
    MICROFRONTEND = "microfrontend"
    WORKER_INTEGRATION = "worker_integration"


@dataclass
class UserStoryDraft:
    id: str
    number: int
    title: str
    persona: str
    prd_id: str
    status: str = "Accepted"
    role: str = ""
    action: str = ""
    benefit: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)

    @property
    def canonical_id(self) -> str:
        clean = self.id.upper().replace("US-", "")
        return f"US-{clean.zfill(4)}"


@dataclass
class TaskDraft:
    id: str
    number: int
    title: str
    status: str = "Proposed"
    dependencies: list[str] = field(default_factory=list)
    governing_adrs: list[str] = field(default_factory=list)
    governing_prds: list[str] = field(default_factory=list)
    governing_stories: list[str] = field(default_factory=list)
    target_release: str = "0.4.0"
    summary: str = ""
    problem_statement: str = ""
    scope_of_work: list[str] = field(default_factory=list)
    invest_evaluation: dict[str, str] = field(default_factory=dict)
    definition_of_done: list[str] = field(default_factory=list)
    slice_type: SliceType = SliceType.DOMAIN_AGGREGATE
    is_spike: bool = False
    target_bc: str = "platform"

    @property
    def canonical_id(self) -> str:
        clean = self.id.upper().replace("TASK-", "")
        return f"TASK-{clean.zfill(4)}"


@dataclass
class DecompositionPlan:
    prd_id: str
    prd_title: str
    spikes: list[TaskDraft] = field(default_factory=list)
    slices: list[TaskDraft] = field(default_factory=list)
    stories: list[UserStoryDraft] = field(default_factory=list)
    replaced_tasks: list[str] = field(default_factory=list)

    @property
    def all_tasks(self) -> list[TaskDraft]:
        return [*self.spikes, *self.slices]


__all__ = [
    "PRD",
    "DecompositionPlan",
    "PRDRecord",
    "PRDStage",
    "PRDStatus",
    "SliceType",
    "TaskDraft",
    "UserStoryDraft",
]
