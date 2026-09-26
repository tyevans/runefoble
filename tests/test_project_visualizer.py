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
    assert m.refined_tasks >= 2
    assert m.ready_buffer_status in ["optimal", "over_buffered", "under_buffered"]


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
