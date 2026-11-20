"""Blackbox tests for The Watcher's configurable call budgets (TASK-0948).

The Watcher, the inference worker and the model server run as live loopback servers. The model
server is a fake OpenAI-compatible endpoint that answers slowly. It is a true process boundary.
A budget that runs out returns 503 within that budget. No substitute output is returned.
"""

from __future__ import annotations

import os
import time
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from inference_worker import api
from inference_worker.llm_factory import build_llm_port
from runefoble_platform.service_credential import SERVICE_CREDENTIAL_HEADER

from tests.helpers.inference_worker_port import install_worker_port
from tests.helpers.live_services import serve
from tests.helpers.spicedb_factory import make_table_runner
from tests.helpers.the_watcher_app import watcher_app
from tests.helpers.watcher_engine import error_fields, select_worker_engine
from tests.helpers.ws_identity import SIGNING_ISSUER

WATCHER_AUTH = {"Authorization": f"Bearer {SIGNING_ISSUER.mint('user-1')}"}
WORKER_AUTH = {SERVICE_CREDENTIAL_HEADER: os.environ["RUNEFOBLE_SERVICE_CREDENTIAL"]}
pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

SPEECH = {
    "speaker_id": "user-1",
    "speaker_name": "Valeros",
    "transcript": "I search the bookshelf for a map",
    "session_id": "sess-1",
    "campaign_id": "camp-1",
}
SLOW_MODEL_S = 4.0


def _empty_board_app() -> FastAPI:
    """Fake board state service with a board that has no tokens."""
    app = FastAPI()

    @app.get("/api/v1/boards/{session_id}")
    async def _board(session_id: str) -> dict:
        return {"session_id": session_id, "tokens": {}}

    return app


@pytest.fixture
def slow_worker_url(monkeypatch: pytest.MonkeyPatch, fake_llm) -> Iterator[str]:
    """A live worker whose model server answers after SLOW_MODEL_S seconds."""
    fake_llm.delay_s = SLOW_MODEL_S
    fake_llm.content = '{"action_type": "dodge", "narrative_flavor": "Valeros ducks."}'
    install_worker_port(monkeypatch, build_llm_port(fake_llm.settings(timeout_seconds=10.0)))
    with serve(api.app) as url:
        yield url


async def _speak(headers: dict[str, str] = WATCHER_AUTH) -> tuple[int, dict]:
    async with AsyncClient(
        transport=ASGITransport(app=watcher_app), base_url="http://test", headers=headers
    ) as ac:
        resp = await ac.post("/api/v1/watcher/transcribe-and-act", json=SPEECH)
    return resp.status_code, resp.json()


@pytest.mark.asyncio
async def test_intent_budget_turns_a_slow_worker_into_503_within_the_budget(
    monkeypatch: pytest.MonkeyPatch, slow_worker_url: str
) -> None:
    """With a 0.5 s intent budget, a worker that answers after 4 s gives 503 in about 0.5 s."""
    await make_table_runner("user-1", "sess-1", "camp-1")
    monkeypatch.setenv("RUNEFOBLE_WATCHER_INTENT_TIMEOUT_S", "0.5")
    select_worker_engine(monkeypatch, slow_worker_url)

    with serve(_empty_board_app()) as board_url:
        monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", board_url)
        started = time.monotonic()
        status, body = await _speak()
        elapsed = time.monotonic() - started

    assert status == 503
    assert error_fields(body["detail"]) == {
        "error": "backend_unavailable",
        "backend": "inference_worker",
    }
    assert elapsed < 0.5 + 1.0


@pytest.mark.asyncio
async def test_default_intent_budget_is_two_seconds(
    monkeypatch: pytest.MonkeyPatch, slow_worker_url: str
) -> None:
    """With no budget set, the intent call gives up after 2 s, well before the 4 s model reply."""
    await make_table_runner("user-1", "sess-1", "camp-1")
    monkeypatch.delenv("RUNEFOBLE_WATCHER_INTENT_TIMEOUT_S", raising=False)
    select_worker_engine(monkeypatch, slow_worker_url)

    with serve(_empty_board_app()) as board_url:
        monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", board_url)
        started = time.monotonic()
        status, body = await _speak()
        elapsed = time.monotonic() - started

    assert status == 503
    assert error_fields(body["detail"])["backend"] == "inference_worker"
    assert 1.5 < elapsed < SLOW_MODEL_S


@pytest.mark.asyncio
async def test_worker_timeout_setting_bounds_a_slow_model(fake_llm, monkeypatch) -> None:
    """The worker's own timeout bounds the model call. A slow model answers 503 in about 0.5 s."""
    fake_llm.delay_s = SLOW_MODEL_S
    install_worker_port(monkeypatch, build_llm_port(fake_llm.settings(timeout_seconds=0.5)))
    payload = {
        "campaign_id": "camp-1",
        "session_id": "sess-1",
        "speaker_id": "spk-1",
        "speaker_name": "Valeros",
        "transcript": "I search the bookshelf for a map",
        "visible_tokens": [],
    }

    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        started = time.monotonic()
        resp = await ac.post("/inference/v1/intent", json=payload)
        elapsed = time.monotonic() - started

    assert resp.status_code == 503
    assert elapsed < 0.5 + 1.0
