"""Tests for Project Visualizer AGY HTTP endpoints and request validation."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tools.project_visualizer.agy_runner import AgyRunnerManager
    from tools.project_visualizer.server import ThreadingHTTPServer


def _post(url: str, payload: dict) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def test_agy_launch_and_status_endpoints(test_server: tuple[ThreadingHTTPServer, AgyRunnerManager]):
    server, _ = test_server
    base = f"http://127.0.0.1:{server.server_port}"

    # 1. POST /api/agy/launch
    req = {
        "prompt": "Implement TASK-0042",
        "continue_session": False,
        "target_entity_id": "TASK-0042",
    }
    status, body = _post(f"{base}/api/agy/launch", req)
    assert status == 200 and body["status"] == "ok"
    job_id = body["job"]["job_id"]
    assert job_id.startswith("agy-")

    # 2. GET /api/agy/status
    time.sleep(0.15)
    with urllib.request.urlopen(f"{base}/api/agy/status?job_id={job_id}") as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode("utf-8"))
        assert res["job"]["status"] == "completed"
        assert "Mock AGY executed" in res["job"]["output"]

    # 3. GET /api/agy/jobs
    with urllib.request.urlopen(f"{base}/api/agy/jobs") as resp:
        assert resp.status == 200
        jobs_res = json.loads(resp.read().decode("utf-8"))
        assert any(j["job_id"] == job_id for j in jobs_res["jobs"])


def test_agy_endpoint_validation_and_errors(
    test_server: tuple[ThreadingHTTPServer, AgyRunnerManager],
):
    server, _ = test_server
    base = f"http://127.0.0.1:{server.server_port}"

    status, body = _post(f"{base}/api/agy/launch", {"prompt": "   "})
    assert status == 400 and "Prompt cannot be empty" in body["error"]

    with pytest.raises(urllib.error.HTTPError) as exc_400:
        urllib.request.urlopen(f"{base}/api/agy/status")
    assert exc_400.value.code == 400

    with pytest.raises(urllib.error.HTTPError) as exc_404:
        urllib.request.urlopen(f"{base}/api/agy/status?job_id=nonexistent-id")
    assert exc_404.value.code == 404


def test_agy_terminate_endpoint(test_server: tuple[ThreadingHTTPServer, AgyRunnerManager]):
    server, _ = test_server
    base = f"http://127.0.0.1:{server.server_port}"

    status, body = _post(f"{base}/api/agy/launch", {"prompt": "--sleep wait"})
    assert status == 200
    job_id = body["job"]["job_id"]

    time.sleep(0.05)
    term_status, term_body = _post(f"{base}/api/agy/terminate", {"job_id": job_id})
    assert term_status == 200 and term_body["status"] == "ok" and term_body["terminated"] is True
