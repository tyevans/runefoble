"""Blackbox tests for the publish failure policy at the remaining sites (TASK-0693).

Domain-state sites fail the request with 503 and record nothing. Notification sites succeed
and count each failed delivery on ``/healthz``. A failed transcription engine returns 503 from
the public transcribe route and records no speech.

The failing Redis client is a process-boundary double. Every other path uses public HTTP,
WebSocket or stream frontdoors.
"""

from __future__ import annotations

import asyncio
import base64
import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from runefoble_events.events import PlayerSpokeEvent
from runefoble_platform.event_deserializer import deserialize_event
from voice_agent.main import app as voice_app
from voice_agent.stt import get_streaming_pipeline, set_streaming_pipeline

from tests.helpers.audio_synth import generate_pcm_sine
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.module_state import SeamRestorer
from tests.helpers.spicedb_factory import grant_voice_session
from tests.helpers.voice_identity import voice_auth_headers, voice_ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_voice_issuer")

TRANSCRIBE_URL = "/api/v1/voice/transcribe"
BARGE_IN_URL = "/api/v1/voice/filters/barge-in/evaluate"
SESSION_STREAM = "runefoble.events.session"


class FailingRedis(MockAsyncRedis):
    """Redis double whose stream writes always fail, as when the broker is unreachable."""

    async def xadd(self, *args, **kwargs):
        raise ConnectionError("redis unavailable (test double)")


def _stream_events(mock_redis: MockAsyncRedis, stream: str) -> list:
    return [deserialize_event(fields) for _id, fields in mock_redis.streams.get(stream, [])]


def _publish_failures(client: TestClient) -> int:
    return client.get("/healthz").json()["event_publish_failures"]


def _granted_session(speaker_id: str, session_id: str | None = None) -> str:
    """Return a session id whose campaign the test DM runs and where the speaker plays."""
    session_id = session_id or str(uuid.uuid4())
    asyncio.run(grant_voice_session(session_id, players=[speaker_id]))
    return session_id


def _transcribe_body(**extra) -> dict:
    return {
        "speaker_id": "spk-policy-1",
        "speaker_name": "Valeros",
        "session_id": _granted_session("spk-policy-1"),
        "campaign_id": str(uuid.uuid4()),
        "transcript": "I move 3 squares north",
        **extra,
    }


@pytest.fixture
def production_engine_client(
    monkeypatch: pytest.MonkeyPatch,
    mock_redis: MockAsyncRedis,
    tmp_path: Path,
    use_redis_client,
    seam_restorer: SeamRestorer,
) -> Generator[TestClient]:
    """Voice app wired to the production engine, forced unavailable through settings."""
    monkeypatch.setenv("RUNEFOBLE_VOICE_STT_MODEL_SIZE", "runefoble-missing-model")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("HF_HOME", str(tmp_path / "hf-cache"))
    seam_restorer.replace(get_streaming_pipeline, set_streaming_pipeline, None)
    use_redis_client(mock_redis)
    yield TestClient(voice_app, headers=voice_auth_headers())


def test_transcribe_returns_503_and_records_nothing_when_player_event_unpublished(
    client: TestClient, mock_redis: MockAsyncRedis, use_redis_client
):
    """Domain state: a spoken action whose event cannot be published fails with 503."""
    use_redis_client(FailingRedis())

    resp = client.post(TRANSCRIBE_URL, json=_transcribe_body())

    assert resp.status_code == 503, resp.text
    assert resp.json()["event_type"] == "runefoble.events.watcher.player_spoke"
    assert not [
        e for e in _stream_events(mock_redis, SESSION_STREAM) if isinstance(e, PlayerSpokeEvent)
    ]


def test_barge_in_route_succeeds_when_redis_is_down_and_publishes_nothing(
    client: TestClient, use_redis_client
):
    """Barge-in evaluation succeeds when Redis is down. It publishes no event, so none is counted."""
    speech_pcm = generate_pcm_sine(duration_ms=100, freq=440.0, amplitude=9000)
    payload = {
        "session_id": _granted_session("spk-marcus", "sess-policy-barge"),
        "speaker_id": "spk-marcus",
        "speaker_name": "Marcus",
        "audio_base64": base64.b64encode(speech_pcm).decode("ascii"),
        "fade_duration_ms": 20.0,
        "energy_threshold": 350.0,
    }
    before = _publish_failures(client)
    use_redis_client(FailingRedis())

    resp = client.post(BARGE_IN_URL, json=payload)

    assert resp.status_code == 200, resp.text
    assert resp.json()["barge_in_detected"] is True
    assert _publish_failures(client) == before


def test_engine_failure_on_transcribe_route_returns_503_and_records_no_speech(
    production_engine_client: TestClient, mock_redis: MockAsyncRedis
):
    """A transcription engine error returns 503 and records no player speech."""
    body = _transcribe_body(
        audio_base64=base64.b64encode(generate_pcm_sine(duration_ms=300)).decode("ascii"),
    )
    body.pop("transcript")

    resp = production_engine_client.post(TRANSCRIBE_URL, json=body)

    assert resp.status_code == 503, resp.text
    assert resp.json()["detail"]["engine"] == "faster-whisper"
    assert not [
        e for e in _stream_events(mock_redis, SESSION_STREAM) if isinstance(e, PlayerSpokeEvent)
    ]


def test_stream_chunk_publish_failure_is_reported_on_socket_and_not_recorded(
    client: TestClient, mock_redis: MockAsyncRedis, use_redis_client
):
    """Domain state on the stream path: the client gets a publish_failed frame, nothing is kept."""
    use_redis_client(FailingRedis())
    chunk = {
        "session_id": _granted_session("spk-stream-policy"),
        "speaker_id": "spk-stream-policy",
        "speaker_name": "Valeros",
        "audio_data": base64.b64encode(generate_pcm_sine(duration_ms=300)).decode("ascii"),
        "is_final": True,
    }

    with client.websocket_connect(
        f"/api/v1/voice/stream/ws/{chunk['session_id']}/spk-stream-policy"
        "?campaign_id=camp-stream-1&speaker_name=Valeros",
        subprotocols=voice_ws_subprotocols(),
    ) as ws:
        ws.send_json(chunk)
        frame = ws.receive_json()

    assert frame["status"] == "publish_failed"
    assert frame["event_type"] == "runefoble.events.watcher.player_spoke"
    assert not [
        e for e in _stream_events(mock_redis, SESSION_STREAM) if isinstance(e, PlayerSpokeEvent)
    ]


@pytest.mark.parametrize(
    "module_path",
    ["campaign_lore.main", "rules_compendium.main", "inference_worker.api"],
)
def test_service_healthz_reports_publish_failure_counter(module_path: str):
    """Each service health route reports the publish failure counter."""
    import importlib

    app = importlib.import_module(module_path).app
    body = TestClient(app).get("/healthz").json()

    assert isinstance(body["event_publish_failures"], int)
