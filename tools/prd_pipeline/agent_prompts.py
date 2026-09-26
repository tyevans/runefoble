"""Antigravity agent prompt builder for interactive and non-interactive PRD decomposition."""

from __future__ import annotations

from .models import PRD


def build_agent_decomposition_prompt(prd: PRD, next_task_id: str, next_story_id: str) -> str:
    """Builds a rich, invariant-enforcing prompt for Antigravity agy to decompose a PRD."""
    prompt = f"""You are executing the PRD Decomposition Pipeline for {prd.canonical_id}: '{prd.title}'.

================ PRD SPECIFICATION ================
Target Bounded Context: services/{prd.target_bc}
Status: {prd.status}
Persona: {prd.who_for}

Problem Statement:
{prd.problem_statement}

What Good Looks Like:
{chr(10).join([f"- {item}" for item in prd.good_looks_like]) if prd.good_looks_like else "None specified"}

Checkable Outcomes:
{chr(10).join([f"- {item}" for item in prd.checkable_outcomes]) if prd.checkable_outcomes else "None specified"}

Current Linked Stories: {", ".join(prd.linked_stories) if prd.linked_stories else "None"}
Current Implementing Tasks: {", ".join(prd.implementing_tasks) if prd.implementing_tasks else "None"}
===================================================

STARTING SEQUENTIAL ALLOCATIONS:
- Next Task ID: {next_task_id}
- Next User Story ID: {next_story_id}

CRITICAL RULES & GRANULARITY INVARIANTS:
1. Single `agy -p` Pass Sizing: Every task must be small enough to be fully implemented, tested, and documented by an autonomous agent in a single pass (< 500 lines per file, ~200-400 lines of implementation, frontdoor tests).
2. Spikes for ADRs: If {prd.canonical_id} introduces novel architecture, new libraries/frameworks (e.g. 3D WebGL, procedural generation, new protocols), create a dedicated SPIKE task:
   `TASK-XXXX: SPIKE: Architectural Spike and ADR for ...`
3. Vertical Slicing: Decompose user-facing features into thin vertical slices:
   - Domain Event & Aggregate Slice: `eventsource-py` domain events and DeclarativeAggregate.
   - API & Authorization Slice: FastAPI APIRouter, Zitadel JWT auth, and SpiceDB Zanzibar checks.
   - Microfrontend Slice: Lit Web Component in `services/{prd.target_bc}/ui/` with Storybook stories and `/ui/manifest`.
   - Worker / Stream Slice: Asynchronous Redis Streams consumer group worker.
4. Hard Invariant 7: Every task must have a frontdoor blackbox test plan asserting on public HTTP endpoints, WebSockets, or CloudEvents.
5. Registries & Priority Index:
   - Write task files into `docs/project/backlog/proposed/XXXX-<slug>.md`.
   - If missing persona user stories, write them into `docs/project/user_stories/accepted/us-XXXX-<slug>.md` and register in `docs/project/user_stories/REGISTRY.md`.
   - Update `## Implementing Backlog Tasks` and `## Linked User Stories` in `{prd.file_path.relative_to(prd.file_path.parents[3])}`.
   - Append the new tasks to `docs/project/backlog/PRIORITY.md`.
   - Run `python3 -m tools.prd_pipeline.cli sync` to ensure all registry tables are consistent.

Decompose {prd.canonical_id} into granular, vertically-sliced proposed tasks and spikes now.
"""
    return prompt.strip()
