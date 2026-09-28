"""Directory scanner and document parser for PRD files."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from tools.project_visualizer.markdown_utils import (
    detect_target_bc,
    extract_list_items,
    extract_prefixed_ids,
    extract_section,
    parse_frontmatter,
)

from .models import PRDRecord, PRDStage


class PRDScanner:
    """Crawls and parses PRD markdown documents across lifecycle stages."""

    def __init__(self, product_dir: Path | str):
        self.product_dir = Path(product_dir).resolve()

    def list_files(self) -> list[Path]:
        """Finds all PRD markdown files across product subdirectories."""
        files: list[Path] = []
        for stage in PRDStage:
            target_dir = self.product_dir / stage.value
            if target_dir.exists():
                files.extend(sorted(target_dir.glob("prd-*.md")))
        files.extend(sorted(self.product_dir.glob("prd-*.md")))
        return sorted(set(files))

    def parse_file(self, file_path: Path) -> PRDRecord:
        """Parses a single PRD markdown file into a PRDRecord."""
        content = file_path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(content)

        raw_id = meta.get("id")
        if not raw_id:
            m = re.search(r"PRD-(\d+)", content)
            raw_id = m.group(1) if m else file_path.stem.split("-")[1]

        clean_id = str(raw_id).upper().replace("PRD-", "")
        try:
            num = int(clean_id)
        except ValueError:
            num = 0

        canonical_id = f"PRD-{clean_id.zfill(4)}"
        title = meta.get("title", "")
        if not title:
            m_title = re.search(r"^#\s+PRD-\d+\s*[—\-:]\s*(.+)$", body, re.MULTILINE)
            title = m_title.group(1).strip() if m_title else file_path.stem

        status = meta.get(
            "status",
            file_path.parent.name.capitalize()
            if file_path.parent.name in [s.value for s in PRDStage]
            else "Accepted",
        )
        created = str(meta.get("created", datetime.now().strftime("%Y-%m-%d")))

        return PRDRecord(
            id=canonical_id,
            number=num,
            title=title,
            status=status,
            created=created,
            file_path=file_path,
            who_for=extract_section(body, "Who this is for"),
            problem_statement=extract_section(body, "What the person cannot do today"),
            good_looks_like=extract_list_items(extract_section(body, "What good looks like")),
            does_not_do=extract_list_items(extract_section(body, "What this does not do")),
            costs_at_scale=extract_section(body, "What it costs at scale"),
            checkable_outcomes=extract_list_items(extract_section(body, "Checkable Outcomes")),
            linked_stories=extract_prefixed_ids("US", extract_section(body, "Linked User Stories")),
            implementing_tasks=extract_prefixed_ids(
                "TASK", extract_section(body, "Implementing Backlog Tasks")
            ),
            raw_frontmatter=meta,
            body=body,
            target_bc=detect_target_bc(content),
        )

    def scan(self) -> dict[str, PRDRecord]:
        """Loads and parses all PRD documents keyed by canonical ID."""
        return {p.canonical_id: p for f in self.list_files() if (p := self.parse_file(f))}
