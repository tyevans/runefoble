"""Blackbox tests for the stand-in guardrail round trip between The Watcher and the worker.

The Watcher and the inference worker run as real HTTP servers in this process. The LLM backend
is a fake OpenAI-compatible server, which is a true process boundary. No code under test is
mocked. Guardrail policy is set through the public Watcher route only.
"""

import json
import os
import threading
from collections.abc import Iterator
from http.server import ThreadingHTTPServer
from typing import Any

import pytest
from character_sheet.models import StandInGuardrails
from httpx import ASGITransport, AsyncClient
from inference_worker import api
from inference_worker.config import WorkerSettings
from inference_worker.llm_factory import build_llm_port
from runefoble_platform.service_credential import SERVICE_CREDENTIAL_HEADER
from runefoble_platform.stand_in_guardrails import StandInGuardrailPolicy
from the_watcher.main import app as watcher_app
from the_watcher.routers import stand_in as stand_in_router

from tests.helpers.inference_worker_port import install_worker_port
from tests.helpers.live_services import serve
from tests.helpers.spicedb_factory import make_table_runner
from tests.helpers.ws_identity import SIGNING_ISSUER
from tests.test_inference_worker_failure_contract import _FakeLLMHandler, _llm_settings

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


WORKER_AUTH = {SERVICE_CREDENTIAL_HEADER: os.environ["RUNEFOBLE_SERVICE_CREDENTIAL"]}


ACT_PATH = "/api/v1/watcher/stand-in/act"
WORKER_PATH = "/inference/v1/stand-in-action"


def _watcher_act_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "character_name": "Seoni",
        "character_class": "Cleric",
        "penalties": [],
        "scene_context": "Marcus is wounded and the orcs close in",
        "personality_traits": ["valiant"],
        "guardrails": {"protect_allies": ["Marcus"]},
        "session_id": "sess-1",
        "campaign_id": "camp-1",
    }
    payload.update(overrides)
    return payload


def _worker_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "campaign_id": "camp-1",
        "session_id": "sess-1",
        "character_name": "Seoni",
        "character_class": "Cleric",
        "penalties": [],
        "scene_context": "Marcus is wounded and the orcs close in",
        "visible_enemies": ["Orc Chieftain"],
        "visible_allies": ["Marcus"],
        "guardrails": {"protect_allies": ["Marcus"]},
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def worker_backend(monkeypatch: pytest.MonkeyPatch):
    """Point the worker app at a backend. Graphs are rebuilt for that client."""

    def _use(settings: WorkerSettings) -> None:
        install_worker_port(monkeypatch, build_llm_port(settings))

    return _use


@pytest.fixture
def fake_llm_server() -> Iterator[ThreadingHTTPServer]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeLLMHandler)
    server.reply = {"status": 200, "content": "{}"}  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.asyncio
async def test_watcher_returns_guardrails_the_worker_applied(worker_backend, monkeypatch):
    """The worker enforces protect_allies, so The Watcher reports it as applied."""
    await make_table_runner("test-user", "sess-1", "camp-1")
    worker_backend(WorkerSettings(backend="mock"))

    with serve(api.app) as worker_url:
        monkeypatch.setattr(stand_in_router, "INFERENCE_URL", worker_url)
        async with AsyncClient(
            transport=ASGITransport(app=watcher_app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"},
        ) as ac:
            resp = await ac.post(ACT_PATH, json=_watcher_act_payload())

    assert resp.status_code == 200
    assert resp.json()["guardrails_applied"] == ["protect_allies"]


@pytest.mark.asyncio
async def test_watcher_reports_no_guardrail_when_none_was_enforced(worker_backend, monkeypatch):
    """A fighter with avoid_melee and no wounded ally enforces nothing. The list stays empty."""
    await make_table_runner("test-user", "sess-1", "camp-1")
    worker_backend(WorkerSettings(backend="mock"))
    payload = _watcher_act_payload(
        character_class="Fighter",
        scene_context="Orcs in the hall",
        guardrails={"avoid_melee": True},
    )

    with serve(api.app) as worker_url:
        monkeypatch.setattr(stand_in_router, "INFERENCE_URL", worker_url)
        async with AsyncClient(
            transport=ASGITransport(app=watcher_app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"},
        ) as ac:
            resp = await ac.post(ACT_PATH, json=payload)

    assert resp.status_code == 200
    assert resp.json()["guardrails_applied"] == []


@pytest.mark.asyncio
async def test_watcher_rejects_unknown_guardrail_name_with_422():
    """An unknown guardrail name is a client error, not a silently ignored key."""
    payload = _watcher_act_payload(guardrails={"protect_allys": ["Marcus"]})

    async with AsyncClient(
        transport=ASGITransport(app=watcher_app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"},
    ) as ac:
        resp = await ac.post(ACT_PATH, json=payload)

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_worker_rejects_unknown_guardrail_name_with_422(worker_backend):
    worker_backend(WorkerSettings(backend="mock"))
    payload = _worker_payload(guardrails={"protect_allys": ["Marcus"]})

    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        resp = await ac.post(WORKER_PATH, json=payload)

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_llm_reported_guardrails_are_filtered_to_active_policy(
    worker_backend, fake_llm_server
):
    """The model may name guardrails. Only names the request activated are reported."""
    fake_llm_server.reply = {  # type: ignore[attr-defined]
        "status": 200,
        "content": json.dumps(
            {
                "action_type": "cast_spell",
                "target": "Marcus",
                "dialogue": "Hold on, Marcus!",
                "narrative_flavor": "Seoni channels healing light.",
                "mechanics": {},
                "guardrails_applied": ["protect_allies", "avoid_melee"],
            }
        ),
    }
    worker_backend(_llm_settings(fake_llm_server))

    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        resp = await ac.post(WORKER_PATH, json=_worker_payload())

    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "llm"
    assert body["guardrails_applied"] == ["protect_allies"]


@pytest.mark.asyncio
async def test_worker_without_guardrails_reports_none(worker_backend):
    worker_backend(WorkerSettings(backend="mock"))
    payload = _worker_payload(guardrails=None)

    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        resp = await ac.post(WORKER_PATH, json=payload)

    assert resp.status_code == 200
    assert resp.json()["guardrails_applied"] == []


def test_shared_guardrail_policy_declares_every_character_sheet_field():
    """The shared contract must not drop a field that the character sheet stores."""
    shared = set(StandInGuardrailPolicy.model_fields)
    stored = set(StandInGuardrails.model_fields)

    assert shared == stored
