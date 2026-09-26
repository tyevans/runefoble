"""Registry synchronization for PRDs, User Stories, and Backlog Priority."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from tools.project_visualizer.markdown_utils import parse_frontmatter


class RegistrySynchronizer:
    """Synchronizes registry tables and priority indexes across docs/project."""

    def __init__(self, repo_root: Path | str):
        self.repo_root = Path(repo_root).resolve()
        self.product_dir = self.repo_root / "docs" / "project" / "product"
        self.stories_dir = self.repo_root / "docs" / "project" / "user_stories"
        self.backlog_dir = self.repo_root / "docs" / "project" / "backlog"

    def sync_all(self) -> dict[str, int]:
        """Synchronizes all registries and returns updated counts."""
        n_prds = self.sync_prd_registry()
        n_stories = self.sync_story_registry()
        n_tasks = self.sync_backlog_priority()
        return {
            "prds_synced": n_prds,
            "stories_synced": n_stories,
            "tasks_synced": n_tasks,
        }

    def sync_prd_registry(self) -> int:
        """Reconciles docs/project/product/REGISTRY.md with files on disk."""
        registry_file = self.product_dir / "REGISTRY.md"
        prd_files: list[Path] = []
        for subdir in ["shipped", "accepted", "shaped", "idea"]:
            td = self.product_dir / subdir
            if td.exists():
                prd_files.extend(td.glob("prd-*.md"))
        prd_files.extend(self.product_dir.glob("prd-*.md"))
        prd_files = sorted(set(prd_files))

        # Scan actual task locations on disk to repair any stale links in PRD documents
        task_folders: dict[str, str] = {}
        for folder in ["complete", "refined", "proposed"]:
            dir_path = self.backlog_dir / folder
            if dir_path.exists():
                for f in dir_path.glob("*.md"):
                    task_folders[f.name] = folder

        parsed: list[dict[str, Any]] = []

        for p in prd_files:
            content = p.read_text(encoding="utf-8")
            # Repair stale task links in content
            repaired_content = content
            for fname, folder in task_folders.items():
                for wrong_dir in ["refined", "proposed", "complete"]:
                    if (
                        wrong_dir != folder
                        and f"../../backlog/{wrong_dir}/{fname}" in repaired_content
                    ):
                        repaired_content = repaired_content.replace(
                            f"../../backlog/{wrong_dir}/{fname}", f"../../backlog/{folder}/{fname}"
                        )
            if repaired_content != content:
                p.write_text(repaired_content, encoding="utf-8")
                content = repaired_content

            meta, body = parse_frontmatter(content)
            raw_id = meta.get("id") or p.stem.split("-")[1]
            clean_id = str(raw_id).upper().replace("PRD-", "")
            canonical_id = f"PRD-{clean_id.zfill(4)}"
            num = int(clean_id) if clean_id.isdigit() else 9999

            title = meta.get("title", "")
            if not title:
                m_title = re.search(r"^#\s+PRD-\d+\s*[—\-:]\s*(.+)$", body, re.MULTILINE)
                title = m_title.group(1).strip() if m_title else p.stem

            status = meta.get("status", p.parent.name.capitalize())
            created = str(meta.get("created", "2026-09-25"))
            rel_path = f"{p.parent.name}/{p.name}" if p.parent != self.product_dir else p.name

            parsed.append(
                {
                    "num": num,
                    "id": canonical_id,
                    "title": title,
                    "status": status,
                    "date": created,
                    "file": rel_path,
                }
            )

        parsed.sort(key=lambda x: x["num"])
        lines = [
            "# Product Requirement Record (PRD) Registry",
            "",
            "| ID | Title | Status | Date | File |",
            "|---|---|---|---|---|",
        ]
        for item in parsed:
            lines.append(
                f"| {item['id']} | {item['title']} | {item['status']} | {item['date']} | [`{item['file'].split('/')[-1]}`]({item['file']}) |"
            )
        lines.append("")

        registry_file.write_text("\n".join(lines), encoding="utf-8")
        return len(parsed)

    def sync_story_registry(self) -> int:
        """Reconciles docs/project/user_stories/REGISTRY.md with accepted stories."""
        registry_file = self.stories_dir / "REGISTRY.md"
        accepted_dir = self.stories_dir / "accepted"
        if not accepted_dir.exists():
            return 0

        story_files = sorted(accepted_dir.glob("us-*.md"))
        existing_info: dict[str, tuple[str, str, str, str]] = {}
        if registry_file.exists():
            for line in registry_file.read_text(encoding="utf-8").splitlines():
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 7 and parts[1].startswith("US-"):
                    existing_info[parts[1]] = (parts[2], parts[3], parts[4], parts[5])

        parsed: list[dict[str, Any]] = []
        for p in story_files:
            content = p.read_text(encoding="utf-8")
            meta, body = parse_frontmatter(content)
            raw_id = meta.get("id") or p.stem.split("-")[1]
            clean_id = str(raw_id).upper().replace("US-", "")
            canonical_id = f"US-{clean_id.zfill(4)}"
            num = int(clean_id) if clean_id.isdigit() else 9999

            title = meta.get("title", "")
            if not title:
                m_title = re.search(r"^#\s+US-\d+\s*[—\-:]\s*(.+)$", body, re.MULTILINE)
                title = m_title.group(1).strip() if m_title else p.stem

            if canonical_id in existing_info:
                _, persona, prd, status = existing_info[canonical_id]
            else:
                persona = meta.get("persona", "Adventurer")
                prd = meta.get("governing_prd") or meta.get("prd", "PRD-0001")
                status = meta.get("status", "Accepted")

            rel_link = f"accepted/{p.name}"

            parsed.append(
                {
                    "num": num,
                    "id": canonical_id,
                    "title": title,
                    "persona": persona,
                    "prd": prd,
                    "status": status,
                    "file": rel_link,
                }
            )

        parsed.sort(key=lambda x: x["num"])
        lines = [
            "# User Stories Registry",
            "",
            "User stories document end-to-end user value from the perspective of players, game masters, absent participants, spectators, and platform developers.",
            "",
            "| ID | Title | Persona | Governing PRD | Status | File |",
            "|---|---|---|---|---|---|",
        ]
        for item in parsed:
            lines.append(
                f"| {item['id']} | {item['title']} | {item['persona']} | {item['prd']} | {item['status']} | [`{item['file'].split('/')[-1]}`]({item['file']}) |"
            )
        lines.append("")

        registry_file.write_text("\n".join(lines), encoding="utf-8")
        return len(parsed)

    def sync_backlog_priority(self) -> int:
        """Reconciles docs/project/backlog/PRIORITY.md with disk state, repairing stale paths and adding new tasks."""
        priority_file = self.backlog_dir / "PRIORITY.md"
        if not priority_file.exists():
            return 0

        # Scan actual files on disk
        task_locations: dict[str, tuple[str, str, str]] = {}  # tid -> (folder, filename, title)
        for folder in ["complete", "refined", "proposed"]:
            dir_path = self.backlog_dir / folder
            if not dir_path.exists():
                continue
            for f in dir_path.glob("*.md"):
                m = re.search(r"(\d{4})", f.stem)
                if m:
                    tid = f"TASK-{m.group(1)}"
                    content = f.read_text(encoding="utf-8")
                    meta, body = parse_frontmatter(content)
                    title = meta.get("title", "")
                    if not title:
                        m_title = re.search(r"^#\s+TASK-\d+\s*:\s*(.+)$", body, re.MULTILINE)
                        title = m_title.group(1).strip() if m_title else f.stem
                    task_locations[tid] = (folder, f.name, title)

        content = priority_file.read_text(encoding="utf-8")
        lines = content.splitlines()

        header_lines = []
        existing_entries: list[tuple[str, str, str, str]] = []  # (tid, status, path, title)
        seen_tids: set[str] = set()

        in_entries = False
        for line in lines:
            m = re.match(
                r"^\d+\.\s+\*\*(TASK-\d{4})\s*\(([^)]+)\)\*\*:\s+\[`([^`]+)`\]\(([^)]+)\)\s+[—\-]\s+(.+)$",
                line,
            )
            if m:
                in_entries = True
                tid = m.group(1)
                status = m.group(2)
                _ = m.group(3)
                path = m.group(4)
                title = m.group(5).strip()
                seen_tids.add(tid)

                # Check if file has moved on disk
                if tid in task_locations:
                    actual_folder, actual_filename, actual_title = task_locations[tid]
                    correct_status = actual_folder.capitalize()
                    correct_path = f"{actual_folder}/{actual_filename}"
                    existing_entries.append(
                        (tid, correct_status, correct_path, actual_title or title)
                    )
                else:
                    existing_entries.append((tid, status, path, title))
            elif not in_entries:
                header_lines.append(line)

        # Check for unlisted tasks (e.g. newly created proposed tasks)
        unlisted = [tid for tid in task_locations if tid not in seen_tids]
        unlisted.sort(key=lambda x: int(x.split("-")[1]))

        for tid in unlisted:
            folder, fname, title = task_locations[tid]
            status = folder.capitalize()
            path = f"{folder}/{fname}"
            existing_entries.append((tid, status, path, title))

        # Reformat priority list
        out_lines = list(header_lines)
        if out_lines and out_lines[-1].strip() != "":
            out_lines.append("")

        for idx, (tid, status, path, title) in enumerate(existing_entries, start=1):
            fname = path.split("/")[-1]
            out_lines.append(f"{idx}. **{tid} ({status})**: [`{fname}`]({path}) — {title}")

        out_lines.append("")
        priority_file.write_text("\n".join(out_lines), encoding="utf-8")
        return len(existing_entries)
