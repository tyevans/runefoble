"""Tests for Project Visualizer parsers and entity extraction."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools.project_visualizer.git_metadata import GitMetadataHarvester
from tools.project_visualizer.parser import (
    ProjectParser,
    parse_adr_files,
    parse_backlog_files,
    parse_feature_files,
    parse_frontmatter,
    parse_persona_files,
    parse_prd_files,
    parse_roadmap_file,
    parse_user_story_files,
    scan_project,
)
from tools.project_visualizer.parsers import (
    ADRParser,
    BacklogParser,
    ProductParser,
)
from tools.project_visualizer.parsers.markdown_utils import (
    detect_target_bc,
    extract_list_items,
    extract_prefixed_ids,
    extract_section,
)


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def test_parser_extracts_all_entities(repo_root: Path):
    parser = ProjectParser(repo_root)
    data = parser.parse_all()

    # Verify all categories extracted
    assert len(data.personas) >= 5
    assert len(data.adrs) >= 13
    assert len(data.prds) >= 12
    assert len(data.stories) >= 40
    assert len(data.tasks) >= 50
    assert len(data.milestones) >= 4
    assert len(data.features) >= 20

    # Verify Persona properties
    evelyn = next((p for p in data.personas if p.id == "evelyn"), None)
    assert evelyn is not None
    assert "Dungeon Master" in evelyn.role
    assert evelyn.avatar_color == "#F59E0B"
    assert len(evelyn.pain_points) > 0
    assert len(evelyn.goals) > 0

    # Verify ADR properties
    adr1 = next((a for a in data.adrs if a.id == "ADR-0001"), None)
    assert adr1 is not None
    assert "SpiceDB" in adr1.title
    assert adr1.domain == "Security & Auth"

    # Verify PRD properties
    prd1 = next((p for p in data.prds if p.id == "PRD-0001"), None)
    assert prd1 is not None
    assert "The Watcher" in prd1.title
    assert len(prd1.outcomes) > 0

    # Verify User Story properties
    us1 = next((s for s in data.stories if s.id == "US-0001"), None)
    assert us1 is not None
    assert "Marcus" in us1.persona or "Adventurer" in us1.persona
    assert len(us1.acceptance_criteria) > 0

    # Verify Task properties
    t31 = next((t for t in data.tasks if t.id == "TASK-0031"), None)
    assert t31 is not None
    assert t31.status == "Complete"
    assert "ADR-0013" in t31.governing_adrs
    assert t31.target_bc == "board_state"


def test_caching_and_deterministic_fingerprint(repo_root: Path):
    parser = ProjectParser(repo_root)
    data1 = parser.parse_all()
    data2 = parser.parse_all()

    assert data1.data_hash != ""
    assert data1.data_hash == data2.data_hash
    assert data1.last_updated == data2.last_updated
    assert data1 is data2  # Cached instance returned


def test_git_metadata_harvester_and_task_tagging(repo_root: Path):
    shallow_file = repo_root / ".git" / "shallow"
    if shallow_file.exists():
        pytest.skip("Git repository is a shallow clone without commit history")

    harvester = GitMetadataHarvester(repo_root)
    harvested = harvester.harvest()
    assert len(harvested) > 0

    parser = ProjectParser(repo_root)
    data = parser.parse_all()

    # Verify tasks have commits and prs fields populated
    tasks_with_commits = [t for t in data.tasks if len(t.commits) > 0]
    tasks_with_prs = [t for t in data.tasks if len(t.prs) > 0]
    assert len(tasks_with_commits) > 0
    assert len(tasks_with_prs) > 0

    # Specifically check TASK-0041 which has PR #30 in git history
    t41 = next((t for t in data.tasks if t.id == "TASK-0041"), None)
    assert t41 is not None
    assert any("#30" in pr for pr in t41.prs)
    assert any("744383e" in c.hash or "c40d7aa" in c.hash for c in t41.commits)


def test_git_metadata_harvester_parsing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / ".git").mkdir()

    fake_log = (
        "c40d7aa\tTyler Evans\t2026-09-26\tfeat(task-0041): FastMCP Gateway Server Modular Decomposition (#30)\n"
        "744383e\tTy Evans\t2026-09-26\tchore(backlog): complete TASK-0041\n"
    )
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda *args, **kwargs: fake_log,
    )

    harvester = GitMetadataHarvester(tmp_path)
    harvested = harvester.harvest()
    assert "TASK-0041" in harvested
    commits, prs = harvested["TASK-0041"]
    assert len(commits) == 2
    assert "#30" in prs
    assert any(c.hash == "c40d7aa" for c in commits)
    assert any(c.hash == "744383e" for c in commits)


def test_modular_parsers_and_facade_compatibility(repo_root: Path):
    # Test markdown utils facade
    fm, body = parse_frontmatter("---\nid: 1\n---\n# Test\n## Section\n- item 1\n- item 2")
    assert fm["id"] == "1"
    assert extract_section(body, "Section") != ""
    assert extract_list_items(extract_section(body, "Section")) == ["item 1", "item 2"]
    assert detect_target_bc("board_state service") == "board_state"
    assert "ADR-0001" in extract_prefixed_ids("ADR", "Governing ADR-1 and ADR-0002")

    # Test sub-parsers directly
    project_dir = repo_root / "docs" / "project"

    adrs = parse_adr_files(project_dir, repo_root)
    assert len(adrs) >= 13
    adr_parser = ADRParser(project_dir, repo_root)
    assert len(adr_parser.parse()) == len(adrs)

    # Verify ADR-0011 metadata and domain classification
    adr11 = next(a for a in adrs if a.id == "ADR-0011")
    assert adr11.title == "eventsource-py as Core Event Sourcing and Aggregate Engine"
    assert adr11.status == "Accepted"
    assert adr11.domain == "Event Sourcing"
    assert "eventsource-py" in adr11.decision
    assert len(adr11.context) > 0
    assert len(adr11.consequences) > 0

    prds = parse_prd_files(project_dir, repo_root)
    assert len(prds) >= 12
    stories = parse_user_story_files(project_dir, repo_root)
    assert len(stories) >= 40
    personas = parse_persona_files(project_dir, repo_root)
    assert len(personas) >= 5
    features = parse_feature_files(project_dir)
    assert len(features) >= 20

    prod_parser = ProductParser(project_dir, repo_root)
    assert len(prod_parser.parse_prds()) == len(prds)
    assert len(prod_parser.parse_user_stories()) == len(stories)
    assert len(prod_parser.parse_personas()) == len(personas)
    assert len(prod_parser.parse_features()) == len(features)

    tasks = parse_backlog_files(project_dir, repo_root)
    assert len(tasks) >= 50
    milestones = parse_roadmap_file(project_dir)
    assert len(milestones) >= 4

    backlog_parser = BacklogParser(project_dir, repo_root)
    assert len(backlog_parser.parse_tasks()) == len(tasks)
    assert len(backlog_parser.parse_milestones()) == len(milestones)

    # Test scan_project facade
    scanned_data = scan_project(repo_root)
    assert len(scanned_data.adrs) == len(adrs)
    assert len(scanned_data.tasks) == len(tasks)


def test_subparsers_line_length_invariant_under_200(repo_root: Path):
    parsers_dir = repo_root / "tools" / "project_visualizer" / "parsers"
    assert parsers_dir.exists()

    all_files = list(parsers_dir.glob("*.py"))
    assert len(all_files) >= 5
    for f in all_files:
        line_count = len(f.read_text(encoding="utf-8").splitlines())
        assert line_count < 200, (
            f"Parser file {f.name} has {line_count} lines, exceeding 200 lines limit"
        )

    parser_facade = repo_root / "tools" / "project_visualizer" / "parser.py"
    facade_lines = len(parser_facade.read_text(encoding="utf-8").splitlines())
    assert facade_lines < 200, (
        f"parser.py facade has {facade_lines} lines, exceeding 200 lines limit"
    )


def test_adr_parser_resilience(tmp_path: Path):
    """Verify ADR parser handles variations in title header formats gracefully."""
    docs_dir = tmp_path / "docs" / "project"
    adrs_dir = docs_dir / "adrs" / "accepted"
    adrs_dir.mkdir(parents=True)

    # 1. Standard format "# ADR-0011: Title"
    adr_file_1 = adrs_dir / "adr-0011-eventsource-py.md"
    adr_file_1.write_text(
        "# ADR-0011: Event Sourcing Core\n\n## Status\nAccepted\n\n## Context\nContext here\n\n## Decision\nDecision here\n\n## Consequences\nConsequences here",
        encoding="utf-8",
    )

    # 2. Space format "# ADR 0012: Title"
    adr_file_2 = adrs_dir / "adr-0012-bauhaus-theming.md"
    adr_file_2.write_text(
        "# ADR 0012: Bauhaus Theme\n\n## Status\nAccepted\n\n## Context\nContext 2\n\n## Decision\nDecision 2\n\n## Consequences\nConsequences 2",
        encoding="utf-8",
    )

    # 3. Registry file with mapping
    registry = docs_dir / "adrs" / "REGISTRY.md"
    registry.write_text(
        "| ID | Title | Status | Date |\n|---|---|---|---|\n"
        "| ADR-0011 | Canonical Event Sourcing | Accepted | 2026-09-25 |\n",
        encoding="utf-8",
    )

    adrs = parse_adr_files(docs_dir, tmp_path)
    assert len(adrs) == 2

    adr11 = next(a for a in adrs if a.id == "ADR-0011")
    assert adr11.title == "Canonical Event Sourcing"
    assert adr11.domain == "Event Sourcing"

    adr12 = next(a for a in adrs if a.id == "ADR-0012")
    assert adr12.id == "ADR-0012"
    assert adr12.title == "Bauhaus Theme"
    assert adr12.domain == "Frontend & UI"
