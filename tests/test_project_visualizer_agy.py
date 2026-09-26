"""Tests for Project Visualizer Antigravity (AGY) Agent Launcher and GitHub Pages isolation."""

from __future__ import annotations

import json
import sys
import threading
import time
import urllib.request
from pathlib import Path

import pytest

from tools.project_visualizer.agy_runner import AgyRunnerManager
from tools.project_visualizer.generator import ProjectVisualizerGenerator
from tools.project_visualizer.server import ProjectVisualizerHandler, ThreadingHTTPServer


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def mock_agy_bin(tmp_path: Path) -> Path:
    """Create an executable mock agy script that records arguments and prints output."""
    script = tmp_path / "mock_agy.sh"
    content = (
        f"#!{sys.executable}\n"
        "import sys\n"
        "import time\n\n"
        "args = sys.argv[1:]\n"
        "if any('--sleep' in a for a in args):\n"
        "    print('Mock AGY sleeping...', flush=True)\n"
        "    time.sleep(5)\n"
        "    print('Mock AGY woke up', flush=True)\n"
        "    sys.exit(0)\n\n"
        "assert '--dangerously-skip-permissions' in args, 'Missing flag'\n"
        "assert '-p' in args, 'Missing prompt flag'\n"
        "p_idx = args.index('-p')\n"
        "prompt = args[p_idx + 1]\n"
        "has_continue = '-c' in args\n"
        "print(f\"Mock AGY executed: prompt='{prompt}', continue={has_continue}\", flush=True)\n"
        "sys.exit(0)\n"
    )
    script.write_text(content, encoding="utf-8")
    script.chmod(0o755)
    return script


def test_agy_runner_execution_and_lifecycle(repo_root: Path, mock_agy_bin: Path):
    runner = AgyRunnerManager(repo_root, agy_bin=str(mock_agy_bin))

    job = runner.launch_job(
        prompt="Build feature for TASK-0042",
        continue_session=True,
        target_entity_id="TASK-0042",
    )

    assert job.status in ("pending", "running")
    assert job.job_id.startswith("agy-")
    assert job.target_entity_id == "TASK-0042"
    assert job.continue_session is True

    # Wait for completion (mock terminates immediately)
    for _ in range(50):
        if job.status in ("completed", "failed"):
            break
        time.sleep(0.05)

    assert job.status == "completed"
    assert job.exit_code == 0
    assert "Mock AGY executed: prompt='Build feature for TASK-0042', continue=True" in job.output
    assert job.end_time is not None

    # Retrieve from runner registry
    fetched = runner.get_job(job.job_id)
    assert fetched is job

    # List jobs
    recent = runner.list_jobs()
    assert len(recent) == 1
    assert recent[0].job_id == job.job_id


def test_agy_runner_termination(repo_root: Path, mock_agy_bin: Path):
    runner = AgyRunnerManager(repo_root, agy_bin=str(mock_agy_bin))

    # Pass prompt that invokes sleep
    job = runner.launch_job(prompt="--sleep testing timeout")
    time.sleep(0.1)

    assert job.status in ("pending", "running")
    terminated = runner.terminate_job(job.job_id)
    assert terminated is True

    time.sleep(0.1)
    assert job.status == "terminated"
    assert "[Process terminated by user]" in job.output


def test_agy_runner_empty_prompt_validation(repo_root: Path):
    runner = AgyRunnerManager(repo_root)
    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        runner.launch_job("   ")


def test_server_agy_http_endpoints(repo_root: Path, mock_agy_bin: Path):
    generator = ProjectVisualizerGenerator(repo_root)
    runner = AgyRunnerManager(repo_root, agy_bin=str(mock_agy_bin))

    handler_class = type(
        "TestAgyConfiguredHandler",
        (ProjectVisualizerHandler,),
        {"generator": generator, "agy_runner": runner},
    )

    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_class)
    port = server.server_port
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.1)

    try:
        # 1. Test POST /api/agy/launch (valid prompt)
        req_data = json.dumps(
            {
                "prompt": "Implement TASK-0042 public routes",
                "continue_session": False,
                "target_entity_id": "TASK-0042",
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/agy/launch",
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            launch_res = json.loads(resp.read().decode("utf-8"))
            assert launch_res["status"] == "ok"
            job_id = launch_res["job"]["job_id"]
            assert job_id.startswith("agy-")

        # 2. Wait and test GET /api/agy/status
        time.sleep(0.2)
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/agy/status?job_id={job_id}"
        ) as resp:
            assert resp.status == 200
            status_res = json.loads(resp.read().decode("utf-8"))
            assert status_res["job"]["status"] == "completed"
            assert "Mock AGY executed" in status_res["job"]["output"]

        # 3. Test GET /api/agy/jobs
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/agy/jobs") as resp:
            assert resp.status == 200
            jobs_res = json.loads(resp.read().decode("utf-8"))
            assert len(jobs_res["jobs"]) >= 1
            assert any(j["job_id"] == job_id for j in jobs_res["jobs"])

        # 4. Test POST /api/agy/launch with empty prompt (400 validation)
        bad_req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/agy/launch",
            data=json.dumps({"prompt": "   "}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(bad_req)
            pytest.fail("Expected 400 error for empty prompt")
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
            err_data = json.loads(exc.read().decode("utf-8"))
            assert "Prompt cannot be empty" in err_data["error"]

        # 5. Test POST /api/agy/terminate with long job
        long_req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/agy/launch",
            data=json.dumps({"prompt": "--sleep wait"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(long_req) as resp:
            long_job_id = json.loads(resp.read().decode("utf-8"))["job"]["job_id"]

        time.sleep(0.05)
        term_req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/agy/terminate",
            data=json.dumps({"job_id": long_job_id}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(term_req) as resp:
            term_res = json.loads(resp.read().decode("utf-8"))
            assert term_res["status"] == "ok"
            assert term_res["terminated"] is True

    finally:
        server.shutdown()
        server.server_close()


def test_static_build_strict_github_pages_isolation(repo_root: Path, tmp_path: Path):
    """Verify AGY launcher UI, modal, and scripts are strictly isolated to live dev server.

    In static distribution mode (make docs-build, make visualize-project-build),
    zero AGY agent execution elements must leak into the published bundle for GitHub Pages.
    """
    generator = ProjectVisualizerGenerator(repo_root)

    # 1. Static build (is_live_server=False)
    static_bundle = generator.build_file(tmp_path / "project-visualizer.html", is_live_server=False)
    static_html = static_bundle.read_text(encoding="utf-8")

    # Assert ZERO AGY elements in static HTML for GitHub Pages
    assert "agy-header-btn" not in static_html
    assert "agy-modal" not in static_html
    assert "agy_launcher.js" not in static_html
    assert "dangerously-skip-permissions" not in static_html
    assert "Launch AGY" not in static_html
    assert "window.IS_LIVE_SERVER = false;" in static_html

    # 2. Live server build (is_live_server=True)
    live_html = generator.generate_html(is_live_server=True)

    # Assert AGY elements ARE present in live server HTML
    assert "agy-header-btn" in live_html
    assert "agy-modal" in live_html
    assert "agy_launcher.js" in live_html
    assert "dangerously-skip-permissions" in live_html
    assert "Launch AGY" in live_html
    assert "window.IS_LIVE_SERVER = true;" in live_html


def test_client_javascript_syntax_validity(repo_root: Path):
    """Verify all static JavaScript modules and concatenated bundles are 100% valid syntax."""
    import shutil
    import subprocess

    from tools.project_visualizer.assets_js import get_client_js

    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js binary not found for syntax checking")

    # 1. Test every individual static JS module
    static_js_dir = repo_root / "tools" / "project_visualizer" / "static" / "js"
    for js_file in static_js_dir.glob("*.js"):
        proc = subprocess.run([node_bin, "-c", str(js_file)], capture_output=True, text=True)
        assert proc.returncode == 0, f"Syntax error in {js_file.name}: {proc.stderr}"

    # 2. Test live server bundled JS
    live_bundle = get_client_js(is_live_server=True)
    proc_live = subprocess.run([node_bin, "-c"], input=live_bundle, capture_output=True, text=True)
    assert proc_live.returncode == 0, f"Syntax error in live bundle: {proc_live.stderr}"

    # 3. Test static distribution bundled JS
    static_bundle = get_client_js(is_live_server=False)
    proc_static = subprocess.run(
        [node_bin, "-c"], input=static_bundle, capture_output=True, text=True
    )
    assert proc_static.returncode == 0, f"Syntax error in static bundle: {proc_static.stderr}"


def test_server_favicon_endpoint(repo_root: Path):
    """Verify /favicon.ico returns 204 No Content instead of 404 console error."""
    generator = ProjectVisualizerGenerator(repo_root)
    handler_class = type(
        "TestFaviconConfiguredHandler",
        (ProjectVisualizerHandler,),
        {"generator": generator},
    )

    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_class)
    port = server.server_port
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.1)

    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/favicon.ico")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 204
    finally:
        server.shutdown()
        server.server_close()
