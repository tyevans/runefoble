"""File writers and formatters for decomposed tasks and user stories."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .models import TaskDraft, UserStoryDraft


class PlanWriter:
    """Writes decomposed tasks, spikes, and user stories to docs/project."""

    def __init__(self, repo_root: Path | str):
        self.repo_root = Path(repo_root).resolve()
        self.backlog_dir = self.repo_root / "docs" / "project" / "backlog"
        self.stories_dir = self.repo_root / "docs" / "project" / "user_stories" / "accepted"

    def write_task(self, draft: TaskDraft) -> Path:
        """Formats and writes a TaskDraft to docs/project/backlog/proposed/."""
        slug = re.sub(r"[^a-z0-9]+", "-", draft.title.lower()).strip("-")
        filename = f"{str(draft.number).zfill(4)}-{slug}.md"
        target_dir = self.backlog_dir / "proposed"
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / filename

        deps_yaml = (
            "\n".join([f"- {d}" for d in draft.dependencies]) if draft.dependencies else "[]"
        )
        adrs_yaml = (
            "\n".join([f"- {a}" for a in draft.governing_adrs]) if draft.governing_adrs else "[]"
        )
        prds_yaml = (
            "\n".join([f"- {p}" for p in draft.governing_prds]) if draft.governing_prds else "[]"
        )
        stories_yaml = (
            "\n".join([f"- {s}" for s in draft.governing_stories])
            if draft.governing_stories
            else "[]"
        )

        content = f"""---
id: '{str(draft.number).zfill(4)}'
title: {draft.title}
status: Proposed
created: {datetime.now().strftime("%Y-%m-%d")}
dependencies:
{deps_yaml if deps_yaml != "[]" else "  - None"}
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
{chr(10).join([f"- **{a}**" for a in draft.governing_adrs])}

## Product & User Story References
- **Product Requirement**: {", ".join(draft.governing_prds)}
- **Governing User Stories**: {", ".join(draft.governing_stories) if draft.governing_stories else "None specified"}

## Detailed Specification & Implementation Plan
{chr(10).join(draft.scope_of_work)}

## INVEST Criteria Evaluation
- **Independent (I)**: {draft.invest_evaluation.get("Independent", "Decoupled vertical slice.")}
- **Negotiable (N)**: {draft.invest_evaluation.get("Negotiable", "Scope boundaries can be refined.")}
- **Valuable (V)**: {draft.invest_evaluation.get("Valuable", "Delivers tangible platform capability.")}
- **Estimable (E)**: {draft.invest_evaluation.get("Estimable", "Predictable single-pass implementation.")}
- **Small (S)**: {draft.invest_evaluation.get("Small", "All files strictly < 500 lines, executable in one agy -p pass.")}
- **Testable (T)**: {draft.invest_evaluation.get("Testable", "Clear frontdoor blackbox test criteria.")}

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
{chr(10).join([f"{i + 1}. {dod}" for i, dod in enumerate(draft.definition_of_done)])}
"""
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def write_user_story(self, draft: UserStoryDraft) -> Path:
        """Formats and writes a UserStoryDraft to docs/project/user_stories/accepted/."""
        slug = re.sub(r"[^a-z0-9]+", "-", draft.title.lower()).strip("-")
        filename = f"us-{str(draft.number).zfill(4)}-{slug}.md"
        self.stories_dir.mkdir(parents=True, exist_ok=True)
        file_path = self.stories_dir / filename

        content = f"""---
id: '{str(draft.number).zfill(4)}'
title: {draft.title}
persona: {draft.persona}
prd: {draft.prd_id}
status: Accepted
created: {datetime.now().strftime("%Y-%m-%d")}
---

# {draft.canonical_id} — {draft.title}

## Persona
**{draft.persona}**

## User Story
**As a** {draft.role or draft.persona},
**I want to** {draft.action},
**So that** {draft.benefit}.

## Acceptance Criteria
{chr(10).join([f"{i + 1}. {ac}" for i, ac in enumerate(draft.acceptance_criteria)])}
"""
        file_path.write_text(content, encoding="utf-8")
        return file_path
