"""Backlog and user story markdown templating and metadata serialization."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import PRD, TaskDraft, UserStoryDraft

_INVEST_DEFAULTS = {
    "Independent": "Decoupled vertical slice.",
    "Negotiable": "Scope boundaries can be refined.",
    "Valuable": "Delivers tangible platform capability.",
    "Estimable": "Predictable single-pass implementation.",
    "Small": "All files strictly < 500 lines, executable in one agy -p pass.",
    "Testable": "Clear frontdoor blackbox test criteria.",
}


def serialize_yaml_list(items: list[str]) -> str:
    """Serializes a list of strings into YAML array format."""
    return "\n".join([f"- {item}" for item in items]) if items else "[]"


def render_acceptance_criteria(criteria: list[str]) -> str:
    """Renders numbered acceptance criteria list items."""
    return "\n".join([f"{i + 1}. {ac}" for i, ac in enumerate(criteria)])


def format_task_markdown(draft: TaskDraft) -> str:
    """Formats a TaskDraft into markdown with YAML frontmatter."""
    deps_yaml = serialize_yaml_list(draft.dependencies) if draft.dependencies else "  - None"
    adrs_yaml = serialize_yaml_list(draft.governing_adrs)
    prds_yaml = serialize_yaml_list(draft.governing_prds)
    stories_yaml = serialize_yaml_list(draft.governing_stories)
    adrs_md = "\n".join([f"- **{a}**" for a in draft.governing_adrs])
    stories_md = ", ".join(draft.governing_stories) if draft.governing_stories else "None specified"
    scope_md = "\n".join(draft.scope_of_work)
    dod_md = render_acceptance_criteria(draft.definition_of_done)
    created_date = datetime.now().strftime("%Y-%m-%d")

    inv = draft.invest_evaluation
    invest_md = "\n".join(
        f"- **{k} ({k[0]})**: {inv.get(k, _INVEST_DEFAULTS[k])}" for k in _INVEST_DEFAULTS
    )

    return f"""---
id: '{str(draft.number).zfill(4)}'
title: {draft.title}
status: Proposed
created: {created_date}
dependencies:
{deps_yaml}
governing_adrs:
{adrs_yaml}
governing_prds:
{prds_yaml}
governing_stories:
{stories_yaml}
target_release: {draft.target_release}
---

# {draft.canonical_id}: {draft.title}

## Status
Proposed

## Summary
{draft.summary}

## Problem Statement
{draft.problem_statement}

## Governing Architecture & ADRs
{adrs_md}

## Product & User Story References
- **Product Requirement**: {", ".join(draft.governing_prds)}
- **Governing User Stories**: {stories_md}

## Detailed Specification & Implementation Plan
{scope_md}

## INVEST Criteria Evaluation
{invest_md}

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
{dod_md}
"""


def format_user_story_markdown(draft: UserStoryDraft) -> str:
    """Formats a UserStoryDraft into markdown with YAML frontmatter."""
    ac_md = render_acceptance_criteria(draft.acceptance_criteria)
    created_date = datetime.now().strftime("%Y-%m-%d")

    return f"""---
id: '{str(draft.number).zfill(4)}'
title: {draft.title}
persona: {draft.persona}
prd: {draft.prd_id}
status: Accepted
created: {created_date}
---

# {draft.canonical_id} — {draft.title}

## Persona
**{draft.persona}**

## User Story
**As a** {draft.role or draft.persona},
**I want to** {draft.action},
**So that** {draft.benefit}.

## Acceptance Criteria
{ac_md}
"""


def create_user_story_draft(story_id: str, story_num: int, prd: PRD) -> UserStoryDraft:
    """Creates a default UserStoryDraft for a PRD."""
    from .models import UserStoryDraft

    persona = prd.who_for.split()[0] if prd.who_for else "Adventurer"
    return UserStoryDraft(
        id=story_id,
        number=story_num,
        title=f"{prd.title} Experience",
        persona=persona,
        prd_id=prd.canonical_id,
        role=persona,
        action=f"interact with {prd.title.lower()}",
        benefit="experience seamless and immersive gameplay",
        acceptance_criteria=prd.checkable_outcomes or ["Executes within performance limits."],
    )
