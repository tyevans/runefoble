"""Blackbox tests for the whisper.cpp HTTP speech engine (TASK-0833).

A loopback HTTP server stands in for the whisper.cpp process. The tests drive the public
voice routes and read the Redis Streams. They never patch the transcriber and never read
private pipeline state. The server only records the requests that production code sends.
"""

from __future__ import annotations

import asyncio
import base64
import io
import uuid
import wave
from collections.abc import Generator
from email.parser import BytesParser
from email.policy import default
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from runefoble_events.events import PlayerSpokeEvent, VoiceTranscriptionFailed
from runefoble_platform.redis_bus import deserialize_event
from voice_agent.main import app as voice_app
from voice_agent.stt import get_streaming_pipeline, set_streaming_pipeline
from voice_agent.synthesis_engine import get_speech_synthesizer, set_speech_synthesizer

from tests.helpers.audio_synth import generate_pcm_sine
from tests.helpers.local_http_server import LocalHttpServer, RecordedRequest
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.module_state import SeamRestorer
from tests.helpers.spicedb_factory import grant_voice_session
from tests.helpers.voice_identity import voice_auth_headers

pytestmark = pytest.mark.usefixtures("trusted_voice_issuer")

TRANSCRIBE_URL = "/api/v1/voice/transcribe"
SESSION_STREAM = "runefoble.events.session"
VOICE_STREAM = "runefoble.events.voice"
WHISPER_TRANSCRIPT = "I move 3 squares north"
SPEAKER_ID = "spk-whisper-1"
SESSION_ID = "sess-whisper-1"


def _whisper_server_replies(request: RecordedRequest) -> tuple[int, dict]:
    """Behave like a healthy whisper.cpp server."""
    if request.method == "POST" and request.path == "/inference":
        return 200, {"text": f" {WHISPER_TRANSCRIPT} "}
    if request.method == "GET" and request.path == "/health":
        return 200, {"status": "ok"}
    return 404, {"error": "not found"}


@pytest.fixture
def whisper_server() -> Generator[LocalHttpServer]:
    """Loopback whisper.cpp stand-in. Tests may replace its handler before a request."""
    with LocalHttpServer(handler=_whisper_server_replies) as server:
        yield server


@pytest.fixture
def espeak_stub(tmp_path: Path) -> Path:
    """A process-boundary stand-in for espeak-ng. It reports a version and exits 0."""
    stub = tmp_path / "bin" / "espeak-ng"
    stub.parent.mkdir()
    stub.write_text("#!/bin/sh\necho 'eSpeak NG stub'\nexit 0\n", encoding="utf-8")
    stub.chmod(0o755)
    return stub


@pytest.fixture
def whisper_env(
    monkeypatch: pytest.MonkeyPatch,
    espeak_stub: Path,
    whisper_server: LocalHttpServer,
    mock_redis: MockAsyncRedis,
    use_redis_client,
    seam_restorer: SeamRestorer,
) -> Generator[LocalHttpServer]:
    """Voice app wired to the whisper.cpp engine at the loopback server."""
    seam_restorer.replace(get_streaming_pipeline, set_streaming_pipeline, None)
    seam_restorer.replace(get_speech_synthesizer, set_speech_synthesizer, None)
    monkeypatch.setenv("RUNEFOBLE_VOICE_STT_ENGINE", "whisper-cpp")
    monkeypatch.setenv("RUNEFOBLE_VOICE_STT_BASE_URL", whisper_server.url)
    monkeypatch.setenv("RUNEFOBLE_VOICE_TTS_BINARY", str(espeak_stub))
    use_redis_client(mock_redis)
    asyncio.run(grant_voice_session(SESSION_ID, players=[SPEAKER_ID]))
    yield whisper_server


@pytest.fixture
def whisper_client(whisper_env: LocalHttpServer) -> TestClient:
    return TestClient(voice_app, headers=voice_auth_headers())


def _transcribe_body(**extra) -> dict:
    return {
        "speaker_id": SPEAKER_ID,
        "speaker_name": "Valeros",
        "session_id": SESSION_ID,
        "campaign_id": str(uuid.uuid4()),
        "audio_base64": base64.b64encode(generate_pcm_sine(duration_ms=300)).decode("ascii"),
        **extra,
    }


def _stream_events(mock_redis: MockAsyncRedis, stream: str) -> list:
    return [deserialize_event(fields) for _id, fields in mock_redis.streams.get(stream, [])]


def _multipart_fields(request: RecordedRequest) -> dict[str, bytes]:
    """Split a multipart/form-data request body into its named parts."""
    envelope = f"Content-Type: {request.headers['Content-Type']}\r\n\r\n".encode()
    message = BytesParser(policy=default).parsebytes(envelope + request.body)
    return {
        part.get_param("name", header="content-disposition"): part.get_payload(decode=True)
        for part in message.iter_parts()
    }


def test_transcribe_returns_the_text_that_whisper_cpp_produced(
    whisper_client: TestClient, whisper_server: LocalHttpServer
):
    """The caller receives the whisper.cpp transcript, with the surrounding space removed."""
    resp = whisper_client.post(TRANSCRIBE_URL, json=_transcribe_body())

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["transcript"] == WHISPER_TRANSCRIPT
    assert data["source"] == "audio"


def test_utterance_is_sent_as_wav_multipart_to_inference(
    whisper_client: TestClient, whisper_server: LocalHttpServer
):
    """The engine posts the utterance as a WAV file with the JSON response format."""
    whisper_client.post(TRANSCRIBE_URL, json=_transcribe_body())

    (request,) = [r for r in whisper_server.requests if r.path == "/inference"]
    assert request.method == "POST"
    fields = _multipart_fields(request)
    assert fields["response_format"] == b"json"
    assert "temperature" in fields
    audio = fields["file"]
    assert audio[:4] == b"RIFF"
    with wave.open(io.BytesIO(audio), "rb") as wf:
        assert wf.getframerate() == 16000
        assert wf.getnchannels() == 1


def test_transcript_is_recorded_as_the_player_action(
    whisper_client: TestClient, mock_redis: MockAsyncRedis
):
    """The transcript from whisper.cpp becomes the PlayerSpokeEvent text."""
    whisper_client.post(TRANSCRIBE_URL, json=_transcribe_body())

    spoke = [
        e for e in _stream_events(mock_redis, SESSION_STREAM) if isinstance(e, PlayerSpokeEvent)
    ]
    assert [e.transcript for e in spoke] == [WHISPER_TRANSCRIPT]


def test_server_error_returns_503_and_publishes_no_player_spoke(
    whisper_client: TestClient,
    whisper_server: LocalHttpServer,
    mock_redis: MockAsyncRedis,
):
    """A whisper.cpp HTTP error fails the request. No text is invented or stored."""
    whisper_server.handler = lambda _request: (500, {"error": "model crashed"})

    resp = whisper_client.post(TRANSCRIBE_URL, json=_transcribe_body())

    assert resp.status_code == 503, resp.text
    body = resp.json()["detail"]
    assert body["error"] == "speech_engine_unavailable"
    assert body["engine"] == "whisper-cpp"
    assert WHISPER_TRANSCRIPT not in resp.text

    assert not [
        e for e in _stream_events(mock_redis, SESSION_STREAM) if isinstance(e, PlayerSpokeEvent)
    ]
    failures = [
        e
        for e in _stream_events(mock_redis, VOICE_STREAM)
        if isinstance(e, VoiceTranscriptionFailed)
    ]
    assert [f.engine for f in failures] == ["whisper-cpp"]


def test_unreachable_server_returns_503(
    whisper_client: TestClient, whisper_server: LocalHttpServer
):
    """When no server answers at the base URL, the request fails with 503."""
    whisper_server.stop()

    resp = whisper_client.post(TRANSCRIBE_URL, json=_transcribe_body())

    assert resp.status_code == 503, resp.text
    assert resp.json()["detail"]["error"] == "speech_engine_unavailable"
    assert resp.json()["detail"]["engine"] == "whisper-cpp"


def test_health_reports_whisper_cpp_ready_when_server_answers(whisper_client: TestClient):
    """The health route names the engine and reports ready while the server answers."""
    resp = whisper_client.get("/healthz")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ok"
    assert body["stt_engine"] == "whisper-cpp"


def test_health_reports_not_ready_when_server_does_not_answer(
    whisper_client: TestClient, whisper_server: LocalHttpServer
):
    """A stopped whisper.cpp server makes the voice agent report the STT engine as not ready."""
    whisper_server.stop()

    resp = whisper_client.get("/healthz")

    assert resp.status_code == 503, resp.text
    body = resp.json()
    assert body["status"] == "not_ready"
    assert "stt" in body["problems"]


def test_whisper_cpp_without_base_url_stops_start_up(
    monkeypatch: pytest.MonkeyPatch,
    espeak_stub: Path,
    seam_restorer: SeamRestorer,
):
    """whisper-cpp has no default base URL. Start-up fails and names the setting."""
    seam_restorer.replace(get_streaming_pipeline, set_streaming_pipeline, None)
    seam_restorer.replace(get_speech_synthesizer, set_speech_synthesizer, None)
    monkeypatch.setenv("RUNEFOBLE_VOICE_STT_ENGINE", "whisper-cpp")
    monkeypatch.delenv("RUNEFOBLE_VOICE_STT_BASE_URL", raising=False)
    monkeypatch.setenv("RUNEFOBLE_VOICE_TTS_BINARY", str(espeak_stub))

    with pytest.raises(ValueError, match="RUNEFOBLE_VOICE_STT_BASE_URL"), TestClient(voice_app):
        pass
