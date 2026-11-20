"""Blackbox tests: Push to Talk uploads go through the gateway transcribe route (TASK-0946).

The gateway forwards `POST /api/v1/voice/transcribe` with the caller's bearer to a live
voice_agent upstream. voice_agent runs the STT engine that the test composition root selects
(the fixture transcriber) and forwards the transcript to a live loopback Watcher upstream.
The Watcher upstream records the body that it receives, so the test can read the board
origin that voice_agent forwards (TASK-0942). Every call goes through a public frontdoor.
"""

from __future__ import annotations

import asyncio
import base64
import uuid
from collections.abc import Iterator

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from runefoble_platform.config import PlatformSettings
from voice_agent.stt import StreamingAudioPipeline, get_streaming_pipeline, set_streaming_pipeline
from voice_agent.watcher_intent import build_watcher_intent_port

from tests.helpers.audio_synth import generate_wav_sine
from tests.helpers.fixture_transcriber import FixtureTranscriber
from tests.helpers.live_services import serve
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.module_state import SeamRestorer
from tests.helpers.spicedb_factory import grant_voice_session
from tests.helpers.ws_identity import bearer

TRANSCRIBE_PATH = "/api/v1/voice/transcribe"
SPEAKER = "spk-ptt-valeros"
SPOKEN = "move two squares north"
WATCHER_REPLY = {"action_type": "move", "parameters": {}, "watcher_reply": "Staged."}


@pytest.fixture
def watcher_bodies() -> list[dict]:
    return []


@pytest.fixture
def recording_watcher_url(watcher_bodies: list[dict]) -> Iterator[str]:
    """A loopback Watcher upstream that records each speech body and answers with an intent."""
    app = FastAPI()

    @app.post("/api/v1/watcher/transcribe-and-act")
    async def _transcribe(request: Request) -> dict:
        watcher_bodies.append(await request.json())
        return WATCHER_REPLY

    with serve(app) as url:
        yield url


@pytest.fixture
def session_id() -> str:
    sid = str(uuid.uuid4())
    asyncio.run(grant_voice_session(sid, players=[SPEAKER]))
    return sid


@pytest.fixture
def gateway(
    monkeypatch: pytest.MonkeyPatch,
    mock_redis: MockAsyncRedis,
    use_redis_client,
    seam_restorer: SeamRestorer,
    speech_engine: FixtureTranscriber,
    recording_watcher_url: str,
    trusted_ws_issuer,
    voice_agent_upstream: str,
) -> Iterator[TestClient]:
    """The gateway in front of a live voice_agent whose Watcher port points at the recorder."""
    use_redis_client(mock_redis)
    monkeypatch.setenv("RUNEFOBLE_WATCHER_URL", recording_watcher_url)
    seam_restorer.replace(
        get_streaming_pipeline,
        set_streaming_pipeline,
        StreamingAudioPipeline(
            transcriber=speech_engine, watcher=build_watcher_intent_port(PlatformSettings())
        ),
    )
    speech_engine.script(SPOKEN)
    with TestClient(gateway_app) as client:
        yield client


def _upload(session_id: str, **extra: object) -> dict[str, object]:
    wav = generate_wav_sine(duration_ms=400, sample_rate=16000)
    return {
        "speaker_id": SPEAKER,
        "speaker_name": "Valeros",
        "session_id": session_id,
        "campaign_id": str(uuid.uuid4()),
        "audio_base64": base64.b64encode(wav).decode("ascii"),
        **extra,
    }


def test_wav_upload_returns_the_engine_transcript(gateway: TestClient, session_id: str) -> None:
    res = gateway.post(TRANSCRIBE_PATH, json=_upload(session_id), headers=bearer(SPEAKER))

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["transcript"] == SPOKEN
    assert data["source"] == "audio"
    assert data["watcher_intent"] == WATCHER_REPLY
    assert data["watcher_error"] is None


def test_board_origin_reaches_the_watcher_with_the_transcript(
    gateway: TestClient, session_id: str, watcher_bodies: list[dict]
) -> None:
    origin = {"token_id": "tok-valeros", "from_x": 3, "from_y": 4, "grid_cols": 8, "grid_rows": 6}

    res = gateway.post(TRANSCRIBE_PATH, json=_upload(session_id, **origin), headers=bearer(SPEAKER))

    assert res.status_code == 200, res.text
    assert len(watcher_bodies) == 1
    forwarded = watcher_bodies[0]
    assert forwarded["transcript"] == SPOKEN
    assert {key: forwarded[key] for key in origin} == origin


def test_body_without_audio_or_transcript_is_rejected(
    gateway: TestClient, session_id: str, watcher_bodies: list[dict]
) -> None:
    body = _upload(session_id)
    del body["audio_base64"]

    res = gateway.post(TRANSCRIBE_PATH, json=body, headers=bearer(SPEAKER))

    assert res.status_code == 422, res.text
    assert watcher_bodies == []


def test_request_without_bearer_is_unauthorized(
    gateway: TestClient, session_id: str, watcher_bodies: list[dict]
) -> None:
    res = gateway.post(TRANSCRIBE_PATH, json=_upload(session_id))

    assert res.status_code == 401, res.text
    assert watcher_bodies == []


def test_caller_that_is_not_the_speaker_is_forbidden(
    gateway: TestClient, session_id: str, watcher_bodies: list[dict]
) -> None:
    res = gateway.post(TRANSCRIBE_PATH, json=_upload(session_id), headers=bearer("intruder"))

    assert res.status_code == 403, res.text
    assert watcher_bodies == []
