"""Relational entity linking and milestone mapping for project visualizer."""

from __future__ import annotations

import re
from typing import Any

from tools.project_visualizer.models import ProjectData

THRESHOLDS = (
    (14, "M1"),
    (46, "M2"),
    (74, "M3"),
    (99, "M4"),
    (125, "M5"),
    (140, "M6"),
    (154, "M7"),
    (160, "M8"),
    (205, "M9"),
)


def _fmt_ids(prefix: str, text: str) -> list[str]:
    return [
        f"{prefix}-{x.split('-')[-1].zfill(4)}" for x in re.findall(rf"{prefix}-\d+", text, re.I)
    ]


def _sync_task_links(
    raw: str, prefix: str, target: list[str], emap: dict[str, Any], tid: str
) -> None:
    for fid in _fmt_ids(prefix, raw):
        if fid not in target:
            target.append(fid)
    for eid in target:
        if eid in emap and tid not in emap[eid].implementing_tasks:
            emap[eid].implementing_tasks.append(tid)


def link_personas(data: ProjectData) -> None:
    p_by_id = {p.id: p for p in data.personas}
    for s in data.stories:
        p_str = s.persona.lower()
        m = next((p for p in data.personas if p.name.lower() in p_str or p.id in p_str), None)
        m = m or (p_by_id.get(s.persona.split()[0].lower()) if s.persona else None)
        if m and s.id not in m.story_ids:
            m.story_ids.append(s.id)


def link_tasks(data: ProjectData) -> None:
    prds, tasks = {p.id: p for p in data.prds}, {t.id: t for t in data.tasks}
    stories, adrs = {s.id: s for s in data.stories}, {a.id: a for a in data.adrs}
    for prd in data.prds:
        for tid in prd.implementing_tasks:
            if tid in tasks and prd.id not in tasks[tid].governing_prds:
                tasks[tid].governing_prds.append(prd.id)
    for t in data.tasks:
        _sync_task_links(t.raw_markdown, "PRD", t.governing_prds, prds, t.id)
        _sync_task_links(t.raw_markdown, "US", t.governing_stories, stories, t.id)
        _sync_task_links(t.raw_markdown, "ADR", t.governing_adrs, adrs, t.id)


def link_milestones(data: ProjectData) -> None:
    m_map = {tid: m.id for m in data.milestones for tid in m.task_ids}
    for t in data.tasks:
        if t.milestone:
            continue
        if t.id in m_map:
            t.milestone = m_map[t.id]
        elif t.target_release.startswith("1."):
            t.milestone = "M10"
        elif m := re.match(r"0\.(\d+)", t.target_release):
            t.milestone = f"M{int(m.group(1))}"
        else:
            num = re.search(r"\d+", t.id)
            n = int(num.group()) if num else 0
            t.milestone = next((m for th, m in THRESHOLDS if n <= th), "M10")


def link_stories(data: ProjectData) -> None:
    prds, tasks, stories = (
        {p.id: p for p in data.prds},
        {t.id: t for t in data.tasks},
        {s.id: s for s in data.stories},
    )

    def _add_story(pid: str, sid: str) -> None:
        if pid in prds and sid not in prds[pid].linked_stories:
            prds[pid].linked_stories.append(sid)

    for prd in data.prds:
        for sid in prd.linked_stories:
            if sid in stories and not stories[sid].governing_prd:
                stories[sid].governing_prd = prd.id
    for s in data.stories:
        for pid in _fmt_ids("PRD", s.raw_markdown):
            s.governing_prd = s.governing_prd or pid
            _add_story(pid, s.id)
        if s.governing_prd:
            _add_story(s.governing_prd, s.id)
        for aid in _fmt_ids("ADR", s.raw_markdown):
            if aid not in s.governing_adrs:
                s.governing_adrs.append(aid)
        if not s.governing_prd and s.implementing_tasks:
            for tid in s.implementing_tasks:
                task = tasks.get(tid)
                if task and task.governing_prds:
                    s.governing_prd = task.governing_prds[0]
                    _add_story(s.governing_prd, s.id)
                    break
        if not s.governing_prd:
            c_prd = f"PRD-{s.id.split('-')[-1]}"
            if c_prd in prds:
                s.governing_prd = c_prd
                _add_story(c_prd, s.id)
