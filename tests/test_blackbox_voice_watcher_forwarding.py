"""Voice routes report a failed Watcher forward in `watcher_error` (TASK-0732).

The voice pipeline is built with the production Watcher port from the environment. The Watcher
runs as a live loopback upstream, as a 503 stand-in, or not at all (closed port). Every case
keeps the transcript and the published PlayerSpokeEvent.
"""

from __future__ import annotations

import asyncio
import base64
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from runefoble_platform.config import PlatformSettings
from the_watcher.main import app as watcher_app
from voice_agent.main import app as voice_app
from voice_agent.stt import StreamingAudioPipeline, get_streaming_pipeline, set_streaming_pipeline
from voice_agent.watcher_intent import build_watcher_intent_port

from tests.helpers.audio_synth import generate_pcm_silence, generate_pcm_sine
from tests.helpers.fixture_transcriber import FixtureTranscriber
from tests.helpers.live_services import closed_port_url, serve, unavailable_app
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.module_state import SeamRestorer
from tests.helpers.spicedb_factory import VOICE_DM, bind_character_owner, grant_voice_session
from tests.helpers.voice_identity import voice_auth_headers

pytestmark = pytest.mark.usefixtures("trusted_voice_issuer", "trusted_ws_issuer")

SPEAKER = "spk-forward-1"
SPOKEN = "I search the room for hidden doors"


@pytest.fixture
def voice_with_watcher_at(
    mock_redis: MockAsyncRedis,
    speech_engine: FixtureTranscriber,
    use_redis_client,
    seam_restorer: SeamRestorer,
    monkeypatch: pytest.MonkeyPatch,
):
    """Return a function that points the voice pipeline at a Watcher URL and gives a client."""
    use_redis_client(mock_redis)
    seam_restorer.keep(get_streaming_pipeline, set_streaming_pipeline)

    def build(watcher_url: str) -> TestClient:
        monkeypatch.setenv("RUNEFOBLE_WATCHER_URL", watcher_url)
        set_streaming_pipeline(
            StreamingAudioPipeline(
                transcriber=speech_engine, watcher=build_watcher_intent_port(PlatformSettings())
            )
        )
        speech_engine.script(SPOKEN)
        return TestClient(voice_app, headers=voice_auth_headers())

    return build


@pytest.fixture
def session_id() -> str:
    sid = str(uuid.uuid4())

    async def _grant() -> None:
        await grant_voice_session(sid, players=[SPEAKER])
        await bind_character_owner(VOICE_DM, SPEAKER)

    asyncio.run(_grant())
    return sid


@pytest.fixture
def live_watcher() -> Iterator[str]:
    with serve(watcher_app) as url:
        yield url


def _stream_utterance(client: TestClient, session_id: str) -> dict:
    for pcm in (generate_pcm_sine(duration_ms=300), generate_pcm_silence(duration_ms=200)):
        resp = client.post(
            "/api/v1/voice/stream/chunk",
            json={
                "session_id": session_id,
                "speaker_id": SPEAKER,
                "speaker_name": "Valeros",
                "campaign_id": str(uuid.uuid4()),
                "audio_data": base64.b64encode(pcm).decode("ascii"),
            },
        )
        assert resp.status_code == 200, resp.text
    return resp.json()


def _spoken_events(mock_redis: MockAsyncRedis) -> list:
    return list(mock_redis.streams.get("runefoble.events.session", []))


def test_chunk_reports_unreachable_watcher_and_keeps_transcript(
    voice_with_watcher_at, session_id: str, mock_redis: MockAsyncRedis
):
    client = voice_with_watcher_at(closed_port_url())

    data = _stream_utterance(client, session_id)

    assert data["utterance_complete"] is True
    assert data["transcript"] == SPOKEN
    assert data["event_id"]
    assert data["watcher_intent"] is None
    assert "the_watcher is unreachable" in data["watcher_error"]
    assert len(_spoken_events(mock_redis)) == 1


def test_chunk_reports_watcher_5xx(
    voice_with_watcher_at, session_id: str, mock_redis: MockAsyncRedis
):
    with serve(unavailable_app(503)) as down_url:
        client = voice_with_watcher_at(down_url)
        data = _stream_utterance(client, session_id)

    assert data["transcript"] == SPOKEN
    assert data["watcher_intent"] is None
    assert data["watcher_error"] == "the_watcher failed with HTTP 503"
    assert len(_spoken_events(mock_redis)) == 1


def test_chunk_returns_intent_from_live_watcher(
    voice_with_watcher_at, session_id: str, live_watcher: str
):
    client = voice_with_watcher_at(live_watcher)

    data = _stream_utterance(client, session_id)

    assert data["transcript"] == SPOKEN
    assert data["watcher_error"] is None
    assert data["watcher_intent"] is not None
    assert data["watcher_intent"]["action_type"]


def test_transcribe_reports_unreachable_watcher_and_keeps_transcript(
    voice_with_watcher_at, session_id: str, mock_redis: MockAsyncRedis
):
    client = voice_with_watcher_at(closed_port_url())

    resp = client.post(
        "/api/v1/voice/transcribe",
        json={
            "session_id": session_id,
            "speaker_id": SPEAKER,
            "speaker_name": "Valeros",
            "campaign_id": str(uuid.uuid4()),
            "transcript": SPOKEN,
        },
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["transcript"] == SPOKEN
    assert data["event_id"]
    assert data["watcher_intent"] is None
    assert "the_watcher is unreachable" in data["watcher_error"]
    assert len(_spoken_events(mock_redis)) == 1
