"""Tests for Runefoble docs/project dynamic content visualizer."""

from __future__ import annotations

import json
import threading
import time
import urllib.request
from pathlib import Path

import pytest

from tools.project_visualizer.cli import main as cli_main
from tools.project_visualizer.generator import ProjectVisualizerGenerator
from tools.project_visualizer.graph import ProjectGraphBuilder
from tools.project_visualizer.parser import ProjectParser
from tools.project_visualizer.server import HTTPServer, ProjectVisualizerHandler


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


def test_graph_builder_and_traceability_edges(repo_root: Path):
    parser = ProjectParser(repo_root)
    data = parser.parse_all()
    builder = ProjectGraphBuilder(data)
    builder.build()

    assert len(data.edges) > 100

    # Check edge relations
    relations = {e.relation for e in data.edges}
    assert "desires" in relations
    assert "specifies" in relations
    assert "governed_by" in relations
    assert "deploys_to" in relations

    # Check health metrics
    m = data.metrics
    assert m.total_adrs >= 13
    assert m.total_prds >= 12
    assert m.total_stories >= 40
    assert m.total_tasks >= 50
    assert m.completed_tasks >= 30
    assert m.refined_tasks >= 0
    assert m.ready_buffer_status in ["optimal", "over_buffered", "under_buffered"]


def test_all_prds_have_stories_and_tasks_support(repo_root: Path):
    parser = ProjectParser(repo_root)
    data = parser.parse_all(force=True)
    builder = ProjectGraphBuilder(data)
    builder.build()

    assert len(data.prds) >= 16
    for prd in data.prds:
        assert len(prd.linked_stories) >= 1, f"PRD {prd.id} ({prd.title}) has 0 linked user stories"
        assert len(prd.implementing_tasks) >= 1, (
            f"PRD {prd.id} ({prd.title}) has 0 implementing tasks"
        )

    assert len(data.metrics.orphaned_stories) == 0, (
        f"Found orphaned stories: {data.metrics.orphaned_stories}"
    )


def test_html_generator_produces_valid_bundle(repo_root: Path, tmp_path: Path):
    generator = ProjectVisualizerGenerator(repo_root)
    out_file = tmp_path / "test-visualizer.html"
    result = generator.build_file(out_file)

    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "Runefoble" in content
    assert "INITIAL_PROJECT_DATA" in content
    assert "TASK-0031" in content
    assert "ADR-0001" in content
    assert "PRD-0001" in content
    assert "Traceability Network" in content


def test_cli_subcommands(repo_root: Path, tmp_path: Path):
    # Test stats
    assert cli_main(["stats", "--root", str(repo_root)]) == 0

    # Test build
    out_html = tmp_path / "cli-visualizer.html"
    assert cli_main(["build", "--root", str(repo_root), "--out", str(out_html)]) == 0
    assert out_html.exists()

    # Test export-json
    out_json = tmp_path / "cli-data.json"
    assert cli_main(["export-json", "--root", str(repo_root), "--out", str(out_json)]) == 0
    assert out_json.exists()
    loaded = json.loads(out_json.read_text(encoding="utf-8"))
    assert "metrics" in loaded
    assert "adrs" in loaded
    assert "tasks" in loaded


def test_server_http_endpoints(repo_root: Path):
    generator = ProjectVisualizerGenerator(repo_root)
    handler_class = type(
        "TestConfiguredHandler",
        (ProjectVisualizerHandler,),
        {"generator": generator},
    )

    server = HTTPServer(("127.0.0.1", 0), handler_class)
    port = server.server_port
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.1)

    try:
        # Test GET /
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as resp:
            assert resp.status == 200
            html = resp.read().decode("utf-8")
            assert "<!DOCTYPE html>" in html
            assert "Runefoble" in html

        # Test GET /api/data
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/data") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert len(data["tasks"]) > 0

        # Test GET /api/version
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/version") as resp:
            assert resp.status == 200
            ver = json.loads(resp.read().decode("utf-8"))
            assert "data_hash" in ver
            assert "last_updated" in ver

        # Test GET /api/health
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health") as resp:
            assert resp.status == 200
            health = json.loads(resp.read().decode("utf-8"))
            assert health["status"] == "ok"
            assert health["metrics"]["total_tasks"] > 0

        # Test GET /api/file
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/file?path=docs/project/product/REGISTRY.md"
        ) as resp:
            assert resp.status == 200
            content = resp.read().decode("utf-8")
            assert "PRD" in content

    finally:
        server.shutdown()
        server.server_close()


def test_git_metadata_harvester_and_task_tagging(repo_root: Path):
    from tools.project_visualizer.git_metadata import GitMetadataHarvester

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
    import subprocess

    from tools.project_visualizer.git_metadata import GitMetadataHarvester

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


def test_caching_and_deterministic_fingerprint(repo_root: Path):
    parser = ProjectParser(repo_root)
    data1 = parser.parse_all()
    data2 = parser.parse_all()

    assert data1.data_hash != ""
    assert data1.data_hash == data2.data_hash
    assert data1.last_updated == data2.last_updated
    assert data1 is data2  # Cached instance returned


def test_html_bundle_contains_graph_and_gantt(repo_root: Path, tmp_path: Path):
    generator = ProjectVisualizerGenerator(repo_root)
    out_file = tmp_path / "test-full-visualizer.html"
    result = generator.build_file(out_file)

    content = result.read_text(encoding="utf-8")
    assert "Relationship Graph" in content
    assert "Gantt & Timeline" in content
    assert "Hide Done" in content
    assert "Git Commits & Pull Requests" in content
    assert "ForceSimulation" in content
    assert "graph-minimap" in content
    assert "edge-active-flow" in content
    assert "focus-ripple" in content
    assert "switchGraphLayout" in content


def test_file_length_invariant_strictly_enforced(repo_root: Path):
    vis_dir = repo_root / "tools" / "project_visualizer"
    assert vis_dir.exists()

    all_files = list(vis_dir.glob("*.py")) + list(vis_dir.glob("static/**/*.*"))
    for f in all_files:
        if f.is_file():
            line_count = len(f.read_text(encoding="utf-8").splitlines())
            assert line_count < 500, (
                f"File {f.name} has {line_count} lines, exceeding 500 lines limit"
            )


def test_graph_visualizer_zoom_and_minimap_bundle(repo_root: Path, tmp_path: Path):
    generator = ProjectVisualizerGenerator(repo_root)
    out_file = tmp_path / "test-zoom-minimap.html"
    result = generator.build_file(out_file)

    content = result.read_text(encoding="utf-8")
    # Verify focal mouse zoom anchoring
    assert "zoomGraph(factor, focalX, focalY)" in content or "zoomGraph" in content
    assert "focalX" in content
    assert "focalY" in content
    # Verify minimap real-time node updates and interaction
    assert "mm-node-" in content
    assert "updateMinimap" in content
    assert "moveCameraToMinimapPoint" in content
    assert "minimap-view-rect" in content
    assert "isDraggingMinimap" in content


def test_modular_parsers_and_facade_compatibility(repo_root: Path):
    from tools.project_visualizer.parser import (
        build_traceability_graph,
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
        GraphBuilder,
        ProductParser,
    )
    from tools.project_visualizer.parsers.markdown_utils import (
        detect_target_bc,
        extract_list_items,
        extract_prefixed_ids,
        extract_section,
    )

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

    # Test graph building facade
    built_data = build_traceability_graph(scanned_data)
    assert len(built_data.edges) > 100
    assert built_data.metrics.total_tasks > 0

    builder_instance = GraphBuilder(scanned_data)
    assert builder_instance.build() is built_data


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
