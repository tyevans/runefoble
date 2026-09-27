"""Tests for Project Visualizer HTTP server, endpoints, and CLI commands."""

from __future__ import annotations

import json
import threading
import time
import urllib.request
from pathlib import Path

import pytest

from tools.project_visualizer.cli import main as cli_main
from tools.project_visualizer.generator import ProjectVisualizerGenerator
from tools.project_visualizer.server import HTTPServer, ProjectVisualizerHandler


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


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

        # Test GET /favicon.ico
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/favicon.ico") as resp:
            assert resp.status == 204

    finally:
        server.shutdown()
        server.server_close()


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
