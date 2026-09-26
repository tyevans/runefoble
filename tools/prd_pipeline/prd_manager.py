"""PRD scanning, loading, creation, auditing, and maintenance."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from tools.project_visualizer.markdown_utils import (
    detect_target_bc,
    extract_list_items,
    extract_prefixed_ids,
    extract_section,
    parse_frontmatter,
)

from .models import PRD


class PRDManager:
    """Manages PRD lifecycle files, audits, and registry synchronizations."""

    def __init__(self, repo_root: Path | str):
        self.repo_root = Path(repo_root).resolve()
        self.product_dir = self.repo_root / "docs" / "project" / "product"
        self.backlog_dir = self.repo_root / "docs" / "project" / "backlog"
        self.stories_dir = self.repo_root / "docs" / "project" / "user_stories"

    def list_prd_files(self) -> list[Path]:
        """Finds all PRD markdown files across product subdirectories."""
        files: list[Path] = []
        for subdir in ["idea", "shaped", "accepted", "shipped"]:
            target_dir = self.product_dir / subdir
            if target_dir.exists():
                files.extend(sorted(target_dir.glob("prd-*.md")))
        # Also check root of product_dir just in case
        files.extend(sorted(self.product_dir.glob("prd-*.md")))
        return sorted(set(files))

    def load_prds(self) -> dict[str, PRD]:
        """Loads and parses all PRD documents keyed by canonical ID."""
        prds: dict[str, PRD] = {}
        for p in self.list_prd_files():
            content = p.read_text(encoding="utf-8")
            meta, body = parse_frontmatter(content)

            raw_id = meta.get("id")
            if not raw_id:
                m = re.search(r"PRD-(\d+)", content)
                raw_id = m.group(1) if m else p.stem.split("-")[1]

            clean_id = str(raw_id).upper().replace("PRD-", "")
            try:
                num = int(clean_id)
            except ValueError:
                num = 0

            canonical_id = f"PRD-{clean_id.zfill(4)}"
            title = meta.get("title", "")
            if not title:
                m_title = re.search(r"^#\s+PRD-\d+\s*[—\-:]\s*(.+)$", body, re.MULTILINE)
                title = m_title.group(1).strip() if m_title else p.stem

            status = meta.get(
                "status",
                p.parent.name.capitalize()
                if p.parent.name in ["idea", "shaped", "accepted", "shipped"]
                else "Accepted",
            )
            created = str(meta.get("created", datetime.now().strftime("%Y-%m-%d")))

            who_for = extract_section(body, "Who this is for")
            problem = extract_section(body, "What the person cannot do today")
            good_looks = extract_list_items(extract_section(body, "What good looks like"))
            does_not_do = extract_list_items(extract_section(body, "What this does not do"))
            costs = extract_section(body, "What it costs at scale")
            outcomes = extract_list_items(extract_section(body, "Checkable Outcomes"))

            stories_sec = extract_section(body, "Linked User Stories")
            linked_stories = extract_prefixed_ids("US", stories_sec)

            tasks_sec = extract_section(body, "Implementing Backlog Tasks")
            tasks = extract_prefixed_ids("TASK", tasks_sec)

            target_bc = detect_target_bc(content)

            prds[canonical_id] = PRD(
                id=canonical_id,
                number=num,
                title=title,
                status=status,
                created=created,
                file_path=p,
                who_for=who_for,
                problem_statement=problem,
                good_looks_like=good_looks,
                does_not_do=does_not_do,
                costs_at_scale=costs,
                checkable_outcomes=outcomes,
                linked_stories=linked_stories,
                implementing_tasks=tasks,
                raw_frontmatter=meta,
                body=body,
                target_bc=target_bc,
            )
        return prds

    def get_next_prd_number(self) -> int:
        """Determines the next available integer for PRD numbering."""
        prds = self.load_prds()
        if not prds:
            return 1
        return max(p.number for p in prds.values()) + 1

    def create_prd(
        self,
        title: str,
        persona: str,
        target_bc: str,
        summary: str,
        status: str = "Accepted",
        outcomes: list[str] | None = None,
    ) -> PRD:
        """Creates a new PRD document in the target lifecycle directory."""
        next_num = self.get_next_prd_number()
        prd_id = f"PRD-{str(next_num).zfill(4)}"
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        filename = f"prd-{str(next_num).zfill(4)}-{slug}.md"

        target_dir = self.product_dir / status.lower()
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / filename

        created_date = datetime.now().strftime("%Y-%m-%d")
        outcomes_list = outcomes or [
            f"1. Core {title} capabilities execute with sub-second response times.",
            "2. System state synchronized reliably over WebSockets and Redis Streams.",
            "3. Blackbox frontdoor test suite verifies all user flows.",
        ]

        content = f"""---
id: '{str(next_num).zfill(4)}'
title: {title}
status: {status}
created: {created_date}
---

# {prd_id} — {title}

## Who this is for

{persona} and storytellers seeking advanced capabilities in {target_bc}.

## What the person cannot do today

{summary}

## What good looks like

1. **Core Feature Experience**:
   - Seamless interaction designed for {persona}.
2. **Reliable Distributed Architecture**:
   - Bounded context isolation within `{target_bc}` with event streaming.

## What this does not do

- Does not bypass existing security or Zanzibar authorization.
- Does not couple presentation logic into backend services.

## Checkable Outcomes

{chr(10).join(outcomes_list if outcomes_list[0].startswith("1.") else [f"{i + 1}. {o}" for i, o in enumerate(outcomes_list)])}

## Linked User Stories

*(Stories will be populated by PRD decomposition)*

## Implementing Backlog Tasks

*(Backlog tasks will be populated by PRD decomposition)*
"""
        file_path.write_text(content, encoding="utf-8")
        prds = self.load_prds()
        return prds[prd_id]

    def update_prd_links(
        self,
        prd: PRD,
        tasks: list[tuple[str, str, str]],  # (canonical_id, title, relative_path)
        stories: list[tuple[str, str, str]] | None = None,  # (canonical_id, title, relative_path)
    ) -> None:
        """Updates the Linked User Stories and Implementing Backlog Tasks sections in a PRD file."""
        content = prd.file_path.read_text(encoding="utf-8")

        # Build new tasks section
        tasks_lines = []
        for tid, title, rel_path in sorted(tasks, key=lambda x: x[0]):
            tasks_lines.append(f"- [`{tid}: {title}`]({rel_path})")
        new_tasks_text = "\n".join(tasks_lines)

        # Replace or append Implementing Backlog Tasks
        if "## Implementing Backlog Tasks" in content:
            content = re.sub(
                r"## Implementing Backlog Tasks\s*\n.*?(?=\n##|\Z)",
                f"## Implementing Backlog Tasks\n\n{new_tasks_text}\n",
                content,
                flags=re.DOTALL,
            )
        else:
            content += f"\n## Implementing Backlog Tasks\n\n{new_tasks_text}\n"

        # Build new stories section if provided
        if stories:
            stories_lines = []
            for sid, title, rel_path in sorted(stories, key=lambda x: x[0]):
                stories_lines.append(f"- [`{sid}: {title}`]({rel_path})")
            new_stories_text = "\n".join(stories_lines)

            if "## Linked User Stories" in content:
                content = re.sub(
                    r"## Linked User Stories\s*\n.*?(?=\n##|\Z)",
                    f"## Linked User Stories\n\n{new_stories_text}\n",
                    content,
                    flags=re.DOTALL,
                )
            else:
                content += f"\n## Linked User Stories\n\n{new_stories_text}\n"

        prd.file_path.write_text(content, encoding="utf-8")

    def audit_prds(self) -> dict[str, Any]:
        """Audits PRDs, finding undecomposed PRDs, stale links, and buffer health."""
        prds = self.load_prds()

        complete_tasks = (
            list((self.backlog_dir / "complete").glob("*.md"))
            if (self.backlog_dir / "complete").exists()
            else []
        )
        refined_tasks = (
            list((self.backlog_dir / "refined").glob("*.md"))
            if (self.backlog_dir / "refined").exists()
            else []
        )
        proposed_tasks = (
            list((self.backlog_dir / "proposed").glob("*.md"))
            if (self.backlog_dir / "proposed").exists()
            else []
        )

        all_task_map: dict[str, Path] = {}
        for tp in [*complete_tasks, *refined_tasks, *proposed_tasks]:
            m = re.search(r"(\d{4})", tp.stem)
            if m:
                all_task_map[f"TASK-{m.group(1)}"] = tp

        stale_links: list[dict[str, str]] = []
        undecomposed_prds: list[str] = []
        underdecomposed_prds: list[str] = []
        epic_tasks: list[dict[str, Any]] = []

        # Scan for coarse/epic tasks in proposed
        for tp in proposed_tasks:
            content = tp.read_text(encoding="utf-8")
            scope = extract_section(content, "Scope of Work")
            scope_items = extract_list_items(scope)
            # If a task has 4+ major scope items or mentions building multiple aggregates/microfrontends
            if len(scope_items) >= 4 or "Microservice" in tp.stem or "Engine" in tp.stem:
                m = re.search(r"(\d{4})", tp.stem)
                tid = f"TASK-{m.group(1)}" if m else tp.stem
                epic_tasks.append(
                    {
                        "id": tid,
                        "file": tp.name,
                        "title": tp.stem,
                        "scope_count": len(scope_items),
                    }
                )

        for prd in prds.values():
            if prd.status.lower() in ["accepted", "shaped"]:
                if len(prd.implementing_tasks) == 0:
                    undecomposed_prds.append(prd.canonical_id)
                elif len(prd.implementing_tasks) <= 2:
                    # Check if all implementing tasks are in complete or if they are epic tasks
                    underdecomposed_prds.append(prd.canonical_id)

            # Check stale links in PRD text
            for tid in prd.implementing_tasks:
                if tid in all_task_map:
                    actual_path = all_task_map[tid]
                    # Check if actual path matches relative link in file
                    expected_rel = f"../../backlog/{actual_path.parent.name}/{actual_path.name}"
                    if expected_rel not in prd.body and actual_path.parent.name != "proposed":
                        # Look for wrong directory in text
                        for old_dir in ["refined", "proposed", "complete"]:
                            if (
                                f"../../backlog/{old_dir}/{actual_path.name}" in prd.body
                                and old_dir != actual_path.parent.name
                            ):
                                stale_links.append(
                                    {
                                        "prd": prd.canonical_id,
                                        "task": tid,
                                        "referenced": f"{old_dir}/{actual_path.name}",
                                        "actual": f"{actual_path.parent.name}/{actual_path.name}",
                                    }
                                )

        return {
            "total_prds": len(prds),
            "undecomposed_prds": undecomposed_prds,
            "underdecomposed_prds": underdecomposed_prds,
            "stale_task_links": stale_links,
            "epic_proposed_tasks": epic_tasks,
            "buffer": {
                "complete": len(complete_tasks),
                "refined": len(refined_tasks),
                "proposed": len(proposed_tasks),
                "ready_buffer_low": len(refined_tasks) < 8,
            },
        }
