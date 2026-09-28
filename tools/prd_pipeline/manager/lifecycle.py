"""PRD document creation, auto-increment numbering, and markdown link updates."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .models import PRDRecord


def _update_section(content: str, header: str, items: list[tuple[str, str, str]]) -> str:
    lines = [
        f"- [`{item_id}: {t}`]({rel})" for item_id, t, rel in sorted(items, key=lambda x: x[0])
    ]
    block = f"## {header}\n\n" + "\n".join(lines) + "\n"
    pattern = rf"## {re.escape(header)}\s*\n.*?(?=\n##|\Z)"
    return (
        re.sub(pattern, block, content, flags=re.DOTALL)
        if f"## {header}" in content
        else f"{content.rstrip()}\n\n{block}"
    )


class PRDLifecycle:
    """Handles PRD creation, auto-increment numbering, and link mutations."""

    def __init__(self, product_dir: Path | str):
        self.product_dir = Path(product_dir).resolve()

    def get_next_number(self, prds: dict[str, PRDRecord]) -> int:
        """Determines the next available integer for PRD numbering."""
        return max((p.number for p in prds.values()), default=0) + 1

    def create(
        self,
        title: str,
        persona: str,
        target_bc: str,
        summary: str,
        status: str = "Accepted",
        outcomes: list[str] | None = None,
        next_num: int = 1,
    ) -> tuple[str, Path]:
        """Creates a new PRD document in the target lifecycle directory."""
        prd_id = f"PRD-{str(next_num).zfill(4)}"
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        filename = f"prd-{str(next_num).zfill(4)}-{slug}.md"

        target_dir = self.product_dir / status.lower()
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / filename

        created_date = datetime.now().strftime("%Y-%m-%d")
        raw_outcomes = outcomes or [
            f"1. Core {title} capabilities execute with sub-second response times.",
            "2. System state synchronized reliably over WebSockets and Redis Streams.",
            "3. Blackbox frontdoor test suite verifies all user flows.",
        ]
        outcomes_text = (
            "\n".join(raw_outcomes)
            if raw_outcomes[0].startswith("1.")
            else "\n".join(f"{i + 1}. {o}" for i, o in enumerate(raw_outcomes))
        )

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

{outcomes_text}

## Linked User Stories

*(Stories will be populated by PRD decomposition)*

## Implementing Backlog Tasks

*(Backlog tasks will be populated by PRD decomposition)*
"""
        file_path.write_text(content, encoding="utf-8")
        return prd_id, file_path

    def update_links(
        self,
        prd: PRDRecord,
        tasks: list[tuple[str, str, str]],
        stories: list[tuple[str, str, str]] | None = None,
    ) -> None:
        """Updates Linked User Stories and Implementing Backlog Tasks in a PRD file."""
        content = prd.file_path.read_text(encoding="utf-8")
        content = _update_section(content, "Implementing Backlog Tasks", tasks)
        if stories:
            content = _update_section(content, "Linked User Stories", stories)
        prd.file_path.write_text(content, encoding="utf-8")
