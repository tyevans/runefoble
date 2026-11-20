"""Blackbox tests for TASK-0943: each Watcher engine port has its own setting, and grammar runs first.

The Watcher runs in-process through its public HTTP routes. The inference worker is the real
worker app on a loopback port, and its model runtime is the loopback fake OpenAI server. The
board state service is a loopback HTTP fake. The fake model counts each request, so a test can
prove that the worker was called or not called. No code under test is replaced (ADR-0022).
"""

import json
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from inference_worker import api as worker_api
from inference_worker.llm_factory import build_llm_port
from pydantic import ValidationError
from starlette.testclient import TestClient

from tests.helpers.fake_openai_server import FakeOpenAI
from tests.helpers.inference_worker_port import install_worker_port
from tests.helpers.live_services import closed_port_url, serve
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.spicedb_factory import make_table_runner
from tests.helpers.the_watcher_app import app_built_at_start_up, watcher_app
from tests.helpers.watcher_startup import STARTED_MARKER, start_the_watcher
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

CALLER = "user-1"
GRAMMAR = "I strike the goblin with my sword"
NARRATIVE = "I search the bookshelf for a map"
NOT_UNDERSTOOD = "Not understood."
SESSION = {"session_id": "sess-1", "campaign_id": "camp-1"}
PORT_SETTINGS = (
    "RUNEFOBLE_WATCHER_INTENT_ENGINE",
    "RUNEFOBLE_WATCHER_STAND_IN_ENGINE",
    "RUNEFOBLE_WATCHER_NARRATION_ENGINE",
)


@pytest.fixture
def event_store(mock_bus) -> MockAsyncRedis:
    """Route The Watcher's published events into an in-memory stream store."""
    return mock_bus


@pytest.fixture
def ports_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """No port is configured. Each test enables the port it needs."""
    for name in PORT_SETTINGS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("RUNEFOBLE_INFERENCE_URL", raising=False)
    monkeypatch.delenv("RUNEFOBLE_WATCHER_ENGINE", raising=False)


@pytest.fixture
def llm_worker(monkeypatch: pytest.MonkeyPatch, fake_llm: FakeOpenAI) -> Iterator[str]:
    """The real inference worker on loopback. Its model answers narrative speech as narrative."""
    fake_llm.content = json.dumps(
        {"action_type": "narrative", "narrative_flavor": "Valeros finds a map."}
    )
    install_worker_port(monkeypatch, build_llm_port(fake_llm.settings()))
    with serve(worker_api.app) as url:
        monkeypatch.setenv("RUNEFOBLE_INFERENCE_URL", url)
        yield url


@pytest.fixture
def board_url() -> Iterator[str]:
    """Fake board state service with a board that has no tokens."""
    app = FastAPI()

    @app.get("/api/v1/boards/{session_id}")
    async def _board(session_id: str) -> dict[str, object]:
        return {"session_id": session_id, "tokens": {}}

    with serve(app) as url:
        yield url


def _set_ports(monkeypatch: pytest.MonkeyPatch, **values: str) -> None:
    """Set each port setting by its short name: intent, stand_in or narration."""
    for port, value in values.items():
        monkeypatch.setenv(f"RUNEFOBLE_WATCHER_{port.upper()}_ENGINE", value)


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(CALLER)}"}


async def _speak(transcript: str) -> object:
    await make_table_runner(CALLER, "sess-1", "camp-1")
    payload = {
        "speaker_id": CALLER,
        "speaker_name": "Valeros",
        "transcript": transcript,
        **SESSION,
    }
    async with AsyncClient(
        transport=ASGITransport(app=watcher_app), base_url="http://test", headers=_headers()
    ) as ac:
        return await ac.post("/api/v1/watcher/transcribe-and-act", json=payload)


async def _post(path: str, payload: dict[str, object]) -> object:
    await make_table_runner(CALLER, "sess-1", "camp-1")
    async with AsyncClient(
        transport=ASGITransport(app=watcher_app), base_url="http://test", headers=_headers()
    ) as ac:
        return await ac.post(path, json=payload)


STAND_IN_PAYLOAD = {
    "character_name": "Kyra",
    "character_class": "Cleric",
    "penalties": ["drunk"],
    "scene_context": "Orc raiders attacking bridge",
    **SESSION,
}
NARRATE_PAYLOAD = {
    **SESSION,
    "prompt": "Thunder echoes",
    "scene_environment": "Forgotten Library",
    "tone": "tense_mystery",
}


# --- intent port: grammar first, worker only for narrative speech ---


@pytest.mark.asyncio
async def test_intent_none_parses_an_attack_with_the_grammar(
    ports_off, event_store, llm_worker, board_url, fake_llm, monkeypatch
):
    _set_ports(monkeypatch, intent="none")
    resp = await _speak(GRAMMAR)

    assert resp.status_code == 200
    assert resp.json()["action_type"] == "attack"
    assert resp.json()["source"] == "watcher_rules"
    assert fake_llm.requests == [], "the grammar parsed the move, so no model call is made"


@pytest.mark.asyncio
async def test_intent_worker_still_parses_an_attack_with_the_grammar_only(
    ports_off, event_store, llm_worker, board_url, fake_llm, monkeypatch
):
    _set_ports(monkeypatch, intent="inference_worker")
    monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", board_url)
    resp = await _speak(GRAMMAR)

    assert resp.status_code == 200
    assert resp.json()["action_type"] == "attack"
    assert resp.json()["source"] == "watcher_rules"
    assert fake_llm.requests == []


@pytest.mark.asyncio
async def test_intent_worker_sends_narrative_speech_to_the_llm(
    ports_off, event_store, llm_worker, board_url, fake_llm, monkeypatch
):
    _set_ports(monkeypatch, intent="inference_worker")
    monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", board_url)
    resp = await _speak(NARRATIVE)

    assert resp.status_code == 200
    assert resp.json()["source"] == "llm"
    assert len(fake_llm.requests) == 1


@pytest.mark.asyncio
async def test_intent_worker_down_is_503_and_publishes_no_intent(
    ports_off, event_store, board_url, monkeypatch
):
    _set_ports(monkeypatch, intent="inference_worker")
    monkeypatch.setenv("RUNEFOBLE_INFERENCE_URL", closed_port_url())
    monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", board_url)
    resp = await _speak(NARRATIVE)

    assert resp.status_code == 503
    assert resp.json()["detail"]["error"] == "backend_unavailable"
    assert resp.json()["detail"]["backend"] == "inference_worker"
    assert not event_store.streams, "a failed engine must publish no intent"


@pytest.mark.asyncio
async def test_intent_none_says_not_understood_for_narrative_speech(
    ports_off, event_store, llm_worker, board_url, fake_llm, monkeypatch
):
    _set_ports(monkeypatch, intent="none")
    monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", board_url)
    resp = await _speak(NARRATIVE)

    assert resp.status_code == 200
    assert resp.json()["action_type"] == "narrative"
    assert resp.json()["watcher_reply"] == NOT_UNDERSTOOD
    assert fake_llm.requests == [], "an unconfigured intent port never calls a model"


@pytest.mark.asyncio
async def test_old_engine_setting_has_no_effect(
    ports_off, event_store, llm_worker, board_url, fake_llm, monkeypatch
):
    monkeypatch.setenv("RUNEFOBLE_WATCHER_ENGINE", "inference_worker")
    monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", board_url)
    resp = await _speak(NARRATIVE)
    stand_in = await _post("/api/v1/watcher/stand-in/act", STAND_IN_PAYLOAD)
    narrate = await _post("/api/v1/watcher/narrate", NARRATE_PAYLOAD)

    assert resp.json()["watcher_reply"] == NOT_UNDERSTOOD
    assert fake_llm.requests == []
    assert stand_in.status_code == 503
    assert narrate.status_code == 503


# --- stand-in and narration ports: none is an explicit 503 ---


@pytest.mark.asyncio
async def test_stand_in_none_is_503(ports_off, event_store, llm_worker, monkeypatch, fake_llm):
    _set_ports(monkeypatch, stand_in="none")
    resp = await _post("/api/v1/watcher/stand-in/act", STAND_IN_PAYLOAD)

    assert resp.status_code == 503
    assert resp.json()["detail"]["error"] == "backend_unavailable"
    assert resp.json()["detail"]["backend"] == "none"
    assert fake_llm.requests == []
    assert not event_store.streams


@pytest.mark.asyncio
async def test_narration_none_is_503(ports_off, event_store, llm_worker, monkeypatch, fake_llm):
    _set_ports(monkeypatch, narration="none")
    resp = await _post("/api/v1/watcher/narrate", NARRATE_PAYLOAD)

    assert resp.status_code == 503
    assert resp.json()["detail"]["error"] == "backend_unavailable"
    assert resp.json()["detail"]["backend"] == "none"
    assert fake_llm.requests == []


# --- compound route: single intent follows the intent port rule ---


def _parse_payload(transcript: str) -> dict[str, object]:
    return {
        "speaker_id": CALLER,
        "speaker_name": "Valeros",
        "transcript": transcript,
        "session_id": "sess-1",
        "campaign_id": "camp-1",
    }


@pytest.mark.asyncio
async def test_compound_single_attack_is_grammar_only(
    ports_off, event_store, llm_worker, board_url, fake_llm, monkeypatch
):
    _set_ports(monkeypatch, intent="inference_worker")
    monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", board_url)
    resp = await _post("/api/v1/watcher/intent/parse", _parse_payload(GRAMMAR))

    assert resp.status_code == 200
    assert resp.json()["single_intent"]["action_type"] == "attack"
    assert resp.json()["single_intent"]["source"] == "watcher_rules"
    assert fake_llm.requests == []


@pytest.mark.asyncio
async def test_compound_single_narrative_follows_the_intent_port(
    ports_off, event_store, llm_worker, board_url, fake_llm, monkeypatch
):
    _set_ports(monkeypatch, intent="inference_worker")
    monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", board_url)
    resp = await _post("/api/v1/watcher/intent/parse", _parse_payload(NARRATIVE))

    assert resp.status_code == 200
    assert resp.json()["single_intent"]["source"] == "llm"
    assert len(fake_llm.requests) == 1


@pytest.mark.asyncio
async def test_compound_single_narrative_with_intent_none_is_not_understood(
    ports_off, event_store, llm_worker, board_url, fake_llm, monkeypatch
):
    _set_ports(monkeypatch, intent="none")
    monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", board_url)
    resp = await _post("/api/v1/watcher/intent/parse", _parse_payload(NARRATIVE))

    assert resp.status_code == 200
    assert resp.json()["single_intent"]["watcher_reply"] == NOT_UNDERSTOOD
    assert fake_llm.requests == []


# --- start-up ---


def test_start_up_with_worker_port_and_no_url_fails(monkeypatch):
    for name in PORT_SETTINGS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("RUNEFOBLE_WATCHER_NARRATION_ENGINE", "inference_worker")
    monkeypatch.delenv("RUNEFOBLE_INFERENCE_URL", raising=False)

    with (
        pytest.raises(RuntimeError, match="RUNEFOBLE_INFERENCE_URL is not set"),
        TestClient(app_built_at_start_up()),
    ):
        pass


def test_start_up_with_unknown_port_value_fails(monkeypatch):
    for name in PORT_SETTINGS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("RUNEFOBLE_WATCHER_INTENT_ENGINE", "heuristic")

    with (
        pytest.raises(ValidationError, match="Input should be"),
        TestClient(app_built_at_start_up()),
    ):
        pass


def test_the_watcher_process_refuses_to_start_without_the_inference_url(tmp_path) -> None:
    """The real app lifespan stops start-up and names the missing setting (TASK-0916)."""
    result = start_the_watcher(
        {
            "RUNEFOBLE_WATCHER_INTENT_ENGINE": "inference_worker",
            "RUNEFOBLE_INFERENCE_URL": None,
        },
        tmp_path,
    )
    assert result.returncode != 0
    assert "RUNEFOBLE_INFERENCE_URL" in result.stderr
    assert STARTED_MARKER not in result.stdout
