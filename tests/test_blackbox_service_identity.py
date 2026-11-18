"""Blackbox tests for TASK-0529: game_session and The Watcher verify Zitadel tokens, and the
inference worker requires a service credential (ADR-0015 c and e).

Requests use only public HTTP routes, subprocess start-up, and the worker's public API.
Identity comes from a signed bearer token. Headers such as x-user-id must not grant identity.
"""

from __future__ import annotations

import os
import subprocess
import sys
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as session_app
from httpx import ASGITransport, AsyncClient
from inference_worker import api as worker_api
from inference_worker.config import WorkerSettings
from inference_worker.llm_client import MultiBackendLLMClient
from runefoble_platform.service_credential import SERVICE_CREDENTIAL_HEADER
from the_watcher import dependencies as watcher_dependencies
from the_watcher.main import app as watcher_app
from the_watcher.routers import autonomous_dm

from tests.helpers.spicedb_factory import make_table_runner
from tests.helpers.ws_identity import SIGNING_ISSUER, ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

WORKER_TOKEN = os.environ["RUNEFOBLE_SERVICE_CREDENTIAL"]
PUBLIC_PATHS = {
    "/healthz",
    "/health",
    "/ui/manifest",
    "/game_session/ui/manifest",
    "/the-watcher/ui/manifest",
}
WORKER_PAYLOADS = {
    "/inference/v1/intent": {
        "campaign_id": "camp-1",
        "session_id": "sess-1",
        "speaker_id": "spk-1",
        "speaker_name": "Merisiel",
        "transcript": "I attack the skeleton with my rapier",
        "visible_tokens": [],
    },
    "/inference/v1/dm-narration": {
        "campaign_id": "camp-1",
        "session_id": "sess-1",
        "scene_environment": "Forgotten Library",
        "guidance_prompt": "What do the adventurers see?",
    },
    "/inference/v1/stand-in-action": {
        "campaign_id": "camp-1",
        "session_id": "sess-1",
        "character_name": "Seoni",
        "character_class": "Sorcerer",
        "penalties": ["drunk"],
        "visible_enemies": ["Orc Chieftain"],
    },
}


def _guarded_paths(app) -> list[tuple[str, str]]:
    """Return (method, concrete path) for every documented HTTP operation that is not public."""
    found: list[tuple[str, str]] = []
    for path, operations in app.openapi()["paths"].items():
        if path in PUBLIC_PATHS:
            continue
        concrete = "/".join("x" if part.startswith("{") else part for part in path.split("/"))
        for method in operations:
            found.append((method.upper(), concrete))
    return found


def test_hot_swap_without_bearer_is_refused():
    """Hot-swap no longer skips authorization when the caller sends no identity."""
    client = TestClient(session_app)
    res = client.post(
        f"/api/v1/sessions/{uuid4()}/hot-swap",
        json={"player_id": "p-1", "character_id": str(uuid4())},
    )
    assert res.status_code == 401
    assert res.headers["www-authenticate"] == "Bearer"


def test_hot_swap_identity_is_the_token_subject_not_the_header():
    """A forged x-user-id does not change the acting user. The token subject is checked."""
    client = TestClient(
        session_app,
        headers={
            "Authorization": f"Bearer {SIGNING_ISSUER.mint('intruder')}",
            "x-user-id": "owner-who-has-no-relation-here",
        },
    )
    res = client.post(
        f"/api/v1/sessions/{uuid4()}/hot-swap",
        json={"player_id": "p-1", "character_id": str(uuid4())},
    )
    assert res.status_code == 403
    assert "User 'intruder' does not have permission" in res.json()["detail"]


@pytest.mark.parametrize(("method", "path"), _guarded_paths(session_app))
def test_every_game_session_route_refuses_missing_bearer(method, path):
    client = TestClient(session_app)
    res = client.request(method, path, json={}, headers={"x-user-id": "forged-user"})
    assert res.status_code == 401, f"{method} {path} returned {res.status_code}"


@pytest.mark.parametrize(("method", "path"), _guarded_paths(watcher_app))
def test_every_watcher_route_refuses_missing_bearer(method, path):
    client = TestClient(watcher_app)
    res = client.request(method, path, json={}, headers={"x-user-id": "forged-user"})
    assert res.status_code == 401, f"{method} {path} returned {res.status_code}"


@pytest.mark.asyncio
async def test_worker_refuses_calls_without_service_credential():
    async with AsyncClient(
        transport=ASGITransport(app=worker_api.app), base_url="http://test"
    ) as ac:
        for path, payload in WORKER_PAYLOADS.items():
            res = await ac.post(path, json=payload)
            assert res.status_code == 401, path


@pytest.mark.asyncio
async def test_worker_refuses_wrong_service_credential():
    headers = {SERVICE_CREDENTIAL_HEADER: "not-the-service-credential"}
    async with AsyncClient(
        transport=ASGITransport(app=worker_api.app), base_url="http://test", headers=headers
    ) as ac:
        res = await ac.post("/inference/v1/intent", json=WORKER_PAYLOADS["/inference/v1/intent"])
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_worker_refuses_user_bearer_token():
    """A Zitadel user token is not a service credential."""
    headers = {"Authorization": f"Bearer {SIGNING_ISSUER.mint('user-1')}"}
    async with AsyncClient(
        transport=ASGITransport(app=worker_api.app), base_url="http://test", headers=headers
    ) as ac:
        res = await ac.post("/inference/v1/intent", json=WORKER_PAYLOADS["/inference/v1/intent"])
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_worker_accepts_the_service_credential(monkeypatch):
    monkeypatch.setattr(
        worker_api, "llm_client", MultiBackendLLMClient(WorkerSettings(backend="mock"))
    )
    monkeypatch.setattr(worker_api, "intent_graph", None)
    headers = {SERVICE_CREDENTIAL_HEADER: WORKER_TOKEN}
    async with AsyncClient(
        transport=ASGITransport(app=worker_api.app), base_url="http://test", headers=headers
    ) as ac:
        res = await ac.post("/inference/v1/intent", json=WORKER_PAYLOADS["/inference/v1/intent"])
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_worker_sends_no_cors_headers_to_browser_origins():
    headers = {
        "Origin": "http://evil.test",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization",
    }
    async with AsyncClient(
        transport=ASGITransport(app=worker_api.app), base_url="http://test"
    ) as ac:
        res = await ac.options("/inference/v1/intent", headers=headers)
    assert "access-control-allow-origin" not in res.headers


def _run_worker_import(env_overrides: dict[str, str | None]) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if key != "RUNEFOBLE_SERVICE_CREDENTIAL"}
    for key, value in env_overrides.items():
        if value is not None:
            env[key] = value
    return subprocess.run(
        [sys.executable, "-c", "import inference_worker.api"],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_worker_refuses_to_start_without_service_credential():
    result = _run_worker_import({})
    assert result.returncode != 0
    assert "RUNEFOBLE_SERVICE_CREDENTIAL" in result.stderr


def test_worker_refuses_to_start_with_blank_service_credential():
    result = _run_worker_import({"RUNEFOBLE_SERVICE_CREDENTIAL": "   "})
    assert result.returncode != 0


@pytest.mark.asyncio
async def test_watcher_refuses_to_call_worker_without_configured_credential(monkeypatch):
    """The Watcher does not call the worker without a credential. It reports 503, never a template."""
    monkeypatch.setattr(autonomous_dm, "INFERENCE_URL", "http://worker.invalid:8100")
    monkeypatch.setattr(watcher_dependencies.platform_settings, "service_credential", None)
    await make_table_runner("dm-1", "sess-1", "camp-1")
    async with AsyncClient(
        transport=ASGITransport(app=watcher_app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('dm-1')}"},
    ) as ac:
        res = await ac.post(
            "/api/v1/watcher/narrate",
            json={
                "campaign_id": "camp-1",
                "session_id": "sess-1",
                "scene_environment": "Cellar",
                "tone": "dark_fantasy",
                "prompt": "Describe the room",
            },
        )
    assert res.status_code == 503
    assert res.json()["detail"] == {"error": "backend_unavailable", "backend": "inference_worker"}


def test_default_table_refuses_user_without_patron_seat():
    """The default table has no exemption. A caller without a seat on est-default is refused."""
    client = TestClient(session_app)
    with client.websocket_connect(
        f"/ws/minigames/{uuid4()}", subprotocols=ws_subprotocols("stranger-no-seat")
    ) as ws:
        message = ws.receive_json()
    assert message["code"] == "PERMISSION_DENIED"
