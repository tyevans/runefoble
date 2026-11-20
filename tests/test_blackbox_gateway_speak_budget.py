"""Blackbox test: the gateway waits longer than The Watcher's worst-case speak-and-act (TASK-0948).

The Watcher runs as a live loopback upstream that takes 5.5 s to answer. The gateway must
return that answer with 200. Under the earlier 5.0 s gateway budget it returned 503.
The gateway, its upstreams and the caller's bearer token go through public frontdoors.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.live_services import serve
from tests.helpers.ws_identity import bearer

SPEAK_PATH = "/api/v1/watcher/speak-and-act"
WATCHER_ANSWER_DELAY_S = 5.5
INTENT_REPLY = {"action_type": "dodge", "parameters": {}, "watcher_reply": "Slow.", "source": "llm"}


def _slow_watcher_app() -> FastAPI:
    """A loopback Watcher upstream that answers the speech route after WATCHER_ANSWER_DELAY_S."""
    app = FastAPI()

    @app.post("/api/v1/watcher/transcribe-and-act")
    async def _transcribe() -> dict:
        await asyncio.sleep(WATCHER_ANSWER_DELAY_S)
        return INTENT_REPLY

    return app


@pytest.fixture
def slow_watcher_url(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """Point the gateway at the slow Watcher upstream before the gateway starts."""
    with serve(_slow_watcher_app()) as url:
        monkeypatch.setenv("RUNEFOBLE_WATCHER_URL", url)
        yield url


@pytest.fixture
def gateway(
    slow_watcher_url: str,
    game_session_upstream: str,
    board_state_upstream: str,
    character_sheet_upstream: str,
    voice_agent_upstream: str,
) -> Iterator[TestClient]:
    with TestClient(gateway_app) as client:
        yield client


def test_gateway_waits_past_a_five_and_a_half_second_watcher_answer(gateway: TestClient) -> None:
    body = {
        "speaker_id": "valeros",
        "speaker_name": "Valeros",
        "transcript": "I duck behind the pillar",
        "session_id": str(uuid.uuid4()),
        "campaign_id": str(uuid.uuid4()),
        "from_x": 5,
        "from_y": 5,
        "grid_cols": 12,
        "grid_rows": 12,
    }

    res = gateway.post(SPEAK_PATH, json=body, headers=bearer("valeros"))

    assert res.status_code == 200, res.text
    assert res.json() == INTENT_REPLY
