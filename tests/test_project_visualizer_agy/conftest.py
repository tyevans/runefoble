"""Shared fixtures for Project Visualizer AGY test suite."""

from __future__ import annotations

import sys
import threading
import time
from collections.abc import Generator
from pathlib import Path

import pytest

from tools.project_visualizer.agy_runner import AgyRunnerManager
from tools.project_visualizer.generator import ProjectVisualizerGenerator
from tools.project_visualizer.server import ProjectVisualizerHandler, ThreadingHTTPServer


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def mock_agy_bin(tmp_path: Path) -> Path:
    """Create an executable mock agy script that records arguments and prints output."""
    script = tmp_path / "mock_agy.sh"
    content = (
        f"#!{sys.executable}\nimport sys, time\nargs = sys.argv[1:]\n"
        "if any('--sleep' in a for a in args):\n    time.sleep(5)\n    sys.exit(0)\n"
        "assert '--dangerously-skip-permissions' in args and '-p' in args\n"
        "p = args[args.index('-p') + 1]\n"
        "print(f\"Mock AGY executed: prompt='{p}', continue={'-c' in args}\", flush=True)\n"
    )
    script.write_text(content, encoding="utf-8")
    script.chmod(0o755)
    return script


@pytest.fixture
def test_server(
    repo_root: Path, mock_agy_bin: Path
) -> Generator[tuple[ThreadingHTTPServer, AgyRunnerManager]]:
    generator = ProjectVisualizerGenerator(repo_root)
    runner = AgyRunnerManager(repo_root, agy_bin=str(mock_agy_bin))
    handler = type(
        "TestAgyHandler",
        (ProjectVisualizerHandler,),
        {"generator": generator, "agy_runner": runner},
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.05)
    try:
        yield server, runner
    finally:
        server.shutdown()
        server.server_close()
