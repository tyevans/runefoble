"""Blackbox tests for the stand-in guardrail round trip between The Watcher and the worker.

The Watcher and the inference worker run as real HTTP servers in this process. The LLM backend
is a fake OpenAI-compatible server, which is a true process boundary. No code under test is
mocked. Guardrail policy is set through the public Watcher route only. The worker tells the
model which guardrails are active, and it reports only the names that the model declares and
the request activated.
"""

import json
import os
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from inference_worker import api
from inference_worker.config import WorkerSettings
from inference_worker.llm_factory import build_llm_port
from runefoble_platform.service_credential import SERVICE_CREDENTIAL_HEADER
from runefoble_platform.stand_in_guardrails import StandInGuardrailPolicy

from tests.helpers.fake_openai_server import FakeOpenAI
from tests.helpers.inference_worker_port import install_worker_port
from tests.helpers.live_services import serve
from tests.helpers.spicedb_factory import make_table_runner
from tests.helpers.the_watcher_app import watcher_app
from tests.helpers.watcher_engine import select_worker_engine
from tests.helpers.ws_identity import SIGNING_ISSUER

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


def _decision(**overrides: Any) -> str:
    """A model decision as JSON text. The test sets the guardrails the model declares."""
    document: dict[str, Any] = {
        "action_type": "cast_spell",
        "target": "Marcus",
        "dialogue": "Hold on, Marcus!",
        "narrative_flavor": "Seoni channels healing light.",
        "mechanics": {},
        "guardrails_applied": [],
    }
    document.update(overrides)
    return json.dumps(document)


@pytest.mark.asyncio
async def test_watcher_returns_guardrails_the_worker_applied(
    worker_backend, monkeypatch, fake_llm: FakeOpenAI
):
    """The model declares protect_allies, and the policy activated it, so The Watcher reports it."""
    await make_table_runner("test-user", "sess-1", "camp-1")
    fake_llm.content = _decision(guardrails_applied=["protect_allies"])
    worker_backend(fake_llm.settings())

    with serve(api.app) as worker_url:
        select_worker_engine(monkeypatch, worker_url)
        async with AsyncClient(
            transport=ASGITransport(app=watcher_app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"},
        ) as ac:
            resp = await ac.post(ACT_PATH, json=_watcher_act_payload())

    assert resp.status_code == 200
    assert resp.json()["guardrails_applied"] == ["protect_allies"]
    assert "Protect allies: Marcus" in fake_llm.user_prompts()[-1]


@pytest.mark.asyncio
async def test_watcher_reports_no_guardrail_when_none_was_enforced(
    worker_backend, monkeypatch, fake_llm: FakeOpenAI
):
    """A fighter with avoid_melee whose model declares nothing reports an empty list."""
    await make_table_runner("test-user", "sess-1", "camp-1")
    fake_llm.content = _decision(action_type="attack", guardrails_applied=[])
    worker_backend(fake_llm.settings())
    payload = _watcher_act_payload(
        character_class="Fighter",
        scene_context="Orcs in the hall",
        guardrails={"avoid_melee": True},
    )

    with serve(api.app) as worker_url:
        select_worker_engine(monkeypatch, worker_url)
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
async def test_worker_rejects_unknown_guardrail_name_with_422(worker_backend, fake_llm):
    worker_backend(fake_llm.settings())
    payload = _worker_payload(guardrails={"protect_allys": ["Marcus"]})

    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        resp = await ac.post(WORKER_PATH, json=payload)

    assert resp.status_code == 422
    assert fake_llm.requests == []


@pytest.mark.asyncio
async def test_llm_reported_guardrails_are_filtered_to_active_policy(worker_backend, fake_llm):
    """The model may name guardrails. Only names the request activated are reported."""
    fake_llm.content = _decision(guardrails_applied=["protect_allies", "avoid_melee"])
    worker_backend(fake_llm.settings())
    # avoid_melee is off here, so the model's naming of it must be filtered out.
    payload = _worker_payload(guardrails={"protect_allies": ["Marcus"], "avoid_melee": False})

    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        resp = await ac.post(WORKER_PATH, json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "llm"
    assert body["guardrails_applied"] == ["protect_allies"]


@pytest.mark.asyncio
async def test_worker_omitted_policy_applies_the_shared_default(worker_backend, fake_llm):
    """An omitted policy takes the shared default. The default enables avoid_melee, so the
    model is told to keep out of melee."""
    fake_llm.content = _decision()
    worker_backend(fake_llm.settings())
    payload = _worker_payload(guardrails=None)

    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        resp = await ac.post(WORKER_PATH, json=payload)

    assert resp.status_code == 200
    assert "Avoid frontline melee engagement" in fake_llm.user_prompts()[-1]


def test_shared_guardrail_policy_declares_every_character_sheet_field():
    """The shared contract must not drop a field that the character sheet stores."""
    shared = set(StandInGuardrailPolicy.model_fields)
    stored = set(StandInGuardrailPolicy.model_fields)

    assert shared == stored


@pytest.mark.asyncio
async def test_worker_tells_the_model_to_preserve_spell_slots(worker_backend, fake_llm):
    """preserve_spell_slots reaches the model prompt. The worker reports it only when the model
    declares it."""
    fake_llm.content = _decision(guardrails_applied=["preserve_spell_slots"])
    worker_backend(fake_llm.settings())
    payload = _worker_payload(
        guardrails={"preserve_spell_slots": {"3": 1}, "avoid_melee": False},
        scene_context="Orcs close in",
        visible_allies=[],
    )

    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        resp = await ac.post(WORKER_PATH, json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["action_type"] == "cast_spell"
    assert body["guardrails_applied"] == ["preserve_spell_slots"]
    assert "Preserve spell slots:" in fake_llm.user_prompts()[-1]


@pytest.mark.asyncio
async def test_worker_tells_the_model_the_custom_priorities(worker_backend, fake_llm):
    """custom_priorities reach the model prompt in priority order."""
    fake_llm.content = _decision(target="Goblin Archer", guardrails_applied=["custom_priorities"])
    worker_backend(fake_llm.settings())
    payload = _worker_payload(
        guardrails={"custom_priorities": ["Goblin Archer", "orc chieftain"], "avoid_melee": False},
        visible_enemies=["Orc Chieftain", "Goblin Archer"],
        scene_context="Orcs close in",
        visible_allies=[],
    )

    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        resp = await ac.post(WORKER_PATH, json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["target"] == "Goblin Archer"
    assert body["guardrails_applied"] == ["custom_priorities"]
    assert "Custom priorities: Goblin Archer; orc chieftain" in fake_llm.user_prompts()[-1]
