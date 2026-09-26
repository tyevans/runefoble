"""PRD decomposition planner: heuristics, slice typing, and dependency graph assembly."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from tools.project_visualizer.markdown_utils import detect_target_bc

from .models import PRD, DecompositionPlan, SliceType, TaskDraft
from .templates import create_user_story_draft

SPIKE_KW = r"3d|webgl|relic|alchem|crafting|stl|printable|mesh|particle|leitmotif|dsp|atlas"
UI_KW = r"ui|component|modal|inspector|hud|viewer|canvas|workbench|dashboard|visualizer|standee"
WORKER_KW = r"stream|redis|projection|engine|worker|synthesis|realtime|live|websocket"

_TEMPLATES_FILE = Path(__file__).parent / "slice_templates.json"
_SLICE_DATA: dict[str, dict[str, Any]] = json.loads(_TEMPLATES_FILE.read_text(encoding="utf-8"))


def requires_architectural_spike(prd: PRD) -> bool:
    """Determines if novel technologies or boundaries warrant an ADR spike."""
    return bool(re.search(SPIKE_KW, f"{prd.title} {prd.body}", re.IGNORECASE))


def requires_ui_component(prd: PRD) -> bool:
    """Determines if the PRD includes user-facing presentation."""
    return bool(re.search(UI_KW, f"{prd.title} {prd.body}", re.IGNORECASE))


def requires_worker_slice(prd: PRD) -> bool:
    """Determines if async stream processing or calculation engine is needed."""
    return bool(re.search(WORKER_KW, f"{prd.title} {prd.body}", re.IGNORECASE))


def create_slice_draft(
    slice_type: SliceType,
    task_id: str,
    task_num: int,
    prd: PRD,
    target_bc: str,
    dependencies: list[str],
    governing_stories: list[str],
) -> TaskDraft:
    """Builds a typed TaskDraft for spikes, domain, api, ui, or worker slices."""
    cfg = _SLICE_DATA[slice_type.value]
    slug = re.sub(r"[^a-z0-9]+", "-", prd.title.lower()).strip("-")
    tag = f"runefoble-{slug[:20].strip('-')}"

    def fmt(val: str) -> str:
        return val.format(title=prd.title, bc=target_bc, tag=tag)

    inv = cfg["invest"]
    invest_dict = {
        "Independent": inv[0],
        "Negotiable": inv[1],
        "Valuable": inv[2],
        "Estimable": inv[3],
        "Small": inv[4],
        "Testable": inv[5],
    }

    return TaskDraft(
        id=task_id,
        number=task_num,
        title=fmt(cfg["title"]),
        status="Proposed",
        dependencies=dependencies,
        governing_adrs=cfg["adrs"],
        governing_prds=[prd.canonical_id],
        governing_stories=governing_stories,
        summary=fmt(cfg["summary"]),
        problem_statement=fmt(cfg["problem"]),
        scope_of_work=[fmt(s) for s in cfg["scope"]],
        invest_evaluation=invest_dict,
        definition_of_done=[fmt(d) for d in cfg["dod"]],
        slice_type=slice_type,
        is_spike=(slice_type == SliceType.SPIKE),
        target_bc=target_bc,
    )


def create_spike_draft(tid: str, num: int, prd: PRD, bc: str) -> TaskDraft:
    return create_slice_draft(SliceType.SPIKE, tid, num, prd, bc, [], list(prd.linked_stories))


def create_domain_slice_draft(
    tid: str, num: int, prd: PRD, bc: str, deps: list[str], st: list[str]
) -> TaskDraft:
    return create_slice_draft(SliceType.DOMAIN_AGGREGATE, tid, num, prd, bc, deps, st)


def create_api_slice_draft(
    tid: str, num: int, prd: PRD, bc: str, deps: list[str], st: list[str]
) -> TaskDraft:
    return create_slice_draft(SliceType.API_AUTH, tid, num, prd, bc, deps, st)


def create_ui_slice_draft(
    tid: str, num: int, prd: PRD, bc: str, deps: list[str], st: list[str]
) -> TaskDraft:
    return create_slice_draft(SliceType.MICROFRONTEND, tid, num, prd, bc, deps, st)


def create_worker_slice_draft(
    tid: str, num: int, prd: PRD, bc: str, deps: list[str], st: list[str]
) -> TaskDraft:
    return create_slice_draft(SliceType.WORKER_INTEGRATION, tid, num, prd, bc, deps, st)


class DecompositionPlanner:
    """Plans architectural spikes and vertical slices for a PRD."""

    def __init__(self, current_task_num: int = 0, current_story_num: int = 0):
        self.current_task_num = current_task_num
        self.current_story_num = current_story_num

    def plan(self, prd: PRD) -> DecompositionPlan:
        plan = DecompositionPlan(prd_id=prd.canonical_id, prd_title=prd.title)
        bc = prd.target_bc if prd.target_bc != "platform" else detect_target_bc(prd.title.lower())

        spike_id = None
        if requires_architectural_spike(prd):
            self.current_task_num += 1
            spike_id = f"TASK-{str(self.current_task_num).zfill(4)}"
            plan.spikes.append(create_spike_draft(spike_id, self.current_task_num, prd, bc))

        created_story_ids = list(prd.linked_stories)
        if not created_story_ids:
            self.current_story_num += 1
            story_id = f"US-{str(self.current_story_num).zfill(4)}"
            created_story_ids.append(story_id)
            plan.stories.append(create_user_story_draft(story_id, self.current_story_num, prd))

        t1_id = f"TASK-{str(self.current_task_num + 1).zfill(4)}"
        t2_id = f"TASK-{str(self.current_task_num + 2).zfill(4)}"
        slices: list[tuple[SliceType, list[str]]] = [
            (SliceType.DOMAIN_AGGREGATE, [spike_id] if spike_id else []),
            (SliceType.API_AUTH, [t1_id]),
        ]
        if requires_ui_component(prd):
            slices.append((SliceType.MICROFRONTEND, [t2_id]))
        if requires_worker_slice(prd):
            slices.append((SliceType.WORKER_INTEGRATION, [t1_id]))

        for st, deps in slices:
            self.current_task_num += 1
            task_id = f"TASK-{str(self.current_task_num).zfill(4)}"
            plan.slices.append(
                create_slice_draft(
                    st, task_id, self.current_task_num, prd, bc, deps, created_story_ids
                )
            )

        return plan
