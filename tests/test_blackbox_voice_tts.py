"""Blackbox TDD tests for the Voice Agent TTS adapter and honest synthesis output (TASK-0601).

Drive only public HTTP routes: POST /api/v1/voice/synthesize, POST /api/v1/voice/dsp/apply
and GET /healthz. The fake engine is injected at the composition root. The production
engine is driven through configuration, with a process-boundary stand-in for the binary.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import stat
import wave
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from voice_agent.main import app
from voice_agent.synthesis_engine import set_speech_synthesizer

from tests.helpers.audio_synth import generate_pcm_sine
from tests.helpers.spicedb_factory import grant_voice_session
from tests.helpers.voice_identity import voice_auth_headers


@pytest.fixture(autouse=True)
def _voice_session_grants() -> None:
    """Make the DM and the speakers of these literal sessions authorized through the SpiceDB seam."""
    for session_id in ("session_default",):
        asyncio.run(grant_voice_session(session_id, players=["speaker_default"]))


pytestmark = pytest.mark.usefixtures("trusted_voice_issuer")

TTS_URL = "/api/v1/voice/synthesize"
DSP_URL = "/api/v1/voice/dsp/apply"
SHORT_TEXT = "Hi."
LONG_TEXT = "The ancient dragon exhales a searing blast across the tactical grid."


def _wav_frames(payload_b64: str) -> tuple[int, int]:
    """Return (frame count, sample rate) of the WAV the response carries."""
    with wave.open(io.BytesIO(base64.b64decode(payload_b64)), "rb") as wf:
        return wf.getnframes(), wf.getframerate()


def _write_wav(path: Path, sample_rate: int, frames: int) -> bytes:
    """Write a mono 16-bit WAV of silence and return its bytes."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames * 2))
    data = buffer.getvalue()
    path.write_bytes(data)
    return data


def _speak(client: TestClient, text: str, **extra) -> dict:
    resp = client.post(TTS_URL, json={"text": text, "persona_id": "watcher_dm", **extra})
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture
def client(fake_speech_synthesizer) -> TestClient:
    """Voice app with the fake engine injected at the composition root."""
    return TestClient(app, headers=voice_auth_headers())


@pytest.fixture
def production_tts() -> Generator[None]:
    """Route synthesis through the production adapter. Tests set the binary path."""
    set_speech_synthesizer(None)
    yield
    set_speech_synthesizer(None)


def test_audio_length_grows_with_text_length(client: TestClient):
    """The returned audio depends on the text. A longer text yields more audio."""
    short = _speak(client, SHORT_TEXT)
    long = _speak(client, LONG_TEXT)

    short_frames, _ = _wav_frames(short["audio_base64"])
    long_frames, _ = _wav_frames(long["audio_base64"])
    assert long_frames > short_frames
    assert long["duration_ms"] > short["duration_ms"]


def test_duration_matches_sample_count_and_rate(client: TestClient):
    """duration_ms equals samples divided by sample rate, within 1 ms."""
    data = _speak(client, LONG_TEXT, filters=["ethereal"])

    frames, rate = _wav_frames(data["audio_base64"])
    assert data["sample_rate_hz"] == rate
    assert abs(data["duration_ms"] - frames * 1000.0 / rate) <= 1.0


def test_response_carries_no_stream_urls(client: TestClient):
    """No response field points at a route that does not exist."""
    tts = client.post(TTS_URL, json={"text": LONG_TEXT, "persona_id": "watcher_dm"})
    dsp = client.post(DSP_URL, json={"filters": ["whisper"], "audio_base64": _pcm_b64()})

    for resp in (tts, dsp):
        assert resp.status_code == 200, resp.text
        assert "/streams/" not in resp.text
        assert "audio_stream_url" not in resp.json()


def test_same_text_yields_same_content_hash(client: TestClient):
    """Two calls for the same text return identical audio and the same content hash."""
    first = _speak(client, LONG_TEXT)
    second = _speak(client, LONG_TEXT)

    assert first["content_sha256"] == second["content_sha256"]
    assert (
        hashlib.sha256(base64.b64decode(first["audio_base64"])).hexdigest()
        == (first["content_sha256"])
    )
    assert first["audio_base64"] == second["audio_base64"]


def test_filters_change_the_synthesised_audio(client: TestClient):
    """DSP filters run on the synthesised clip. The same text with a filter yields other audio."""
    plain = _speak(client, LONG_TEXT)
    filtered = _speak(client, LONG_TEXT, filters=["underwater"])

    assert plain["audio_base64"] != filtered["audio_base64"]
    assert "underwater" in filtered["effects_applied"]


def test_responses_carry_one_audio_field_and_one_parameter_field(client: TestClient):
    """Speech and DSP responses carry audio_base64 and dsp_parameters, with no duplicate fields."""
    speech = _speak(client, LONG_TEXT, filters=["ethereal"])
    dsp = client.post(DSP_URL, json={"filters": ["whisper"], "audio_base64": _pcm_b64()})
    assert dsp.status_code == 200, dsp.text

    for body in (speech, dsp.json()):
        assert "audio_base64" in body
        assert "dsp_parameters" in body
        assert "audio_payload" not in body
        assert "dsp_metadata" not in body


def test_empty_text_is_rejected(client: TestClient):
    """An empty text is a client error. The engine is not asked for audio."""
    resp = client.post(TTS_URL, json={"text": "", "persona_id": "watcher_dm"})

    assert resp.status_code == 422


def test_dsp_apply_without_audio_is_rejected(client: TestClient):
    """The DSP route filters supplied audio. Without input it returns 422 and no tone."""
    resp = client.post(DSP_URL, json={"filters": ["whisper"]})

    assert resp.status_code == 422, resp.text
    assert "audio_payload" not in resp.json()


def test_unavailable_engine_returns_503_and_no_audio(
    production_tts: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """When the engine binary is missing, the route fails with 503 and returns no audio."""
    monkeypatch.setenv("RUNEFOBLE_VOICE_TTS_BINARY", str(tmp_path / "missing-espeak-ng"))
    client = TestClient(app, headers=voice_auth_headers())

    resp = client.post(TTS_URL, json={"text": LONG_TEXT, "persona_id": "watcher_dm"})

    assert resp.status_code == 503, resp.text
    detail = resp.json()["detail"]
    assert detail["error"] == "speech_synthesis_unavailable"
    assert detail["engine"] == "espeak-ng"
    assert "audio_base64" not in resp.json()
    assert "audio_payload" not in resp.text


def test_engine_failure_exit_status_returns_503(
    production_tts: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """An engine that exits with an error status is reported, not replaced by a tone."""
    script = tmp_path / "failing-engine"
    script.write_text("#!/bin/sh\necho 'voice data missing' >&2\nexit 2\n")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("RUNEFOBLE_VOICE_TTS_BINARY", str(script))
    client = TestClient(app, headers=voice_auth_headers())

    resp = client.post(TTS_URL, json={"text": LONG_TEXT, "persona_id": "watcher_dm"})

    assert resp.status_code == 503, resp.text
    assert "voice data missing" in resp.json()["detail"]["message"]


def test_production_adapter_returns_the_audio_the_engine_wrote(
    production_tts: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """The production adapter returns the WAV written by the engine process, unchanged."""
    engine_wav = tmp_path / "engine-output.wav"
    original = _write_wav(engine_wav, sample_rate=22050, frames=11025)
    script = tmp_path / "engine"
    script.write_text(f'#!/bin/sh\ncat "{engine_wav}"\n')
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("RUNEFOBLE_VOICE_TTS_BINARY", str(script))
    client = TestClient(app, headers=voice_auth_headers())

    data = _speak(client, LONG_TEXT)

    frames, rate = _wav_frames(data["audio_base64"])
    assert (frames, rate) == (11025, 22050)
    assert data["engine"] == "espeak-ng"
    assert data["sample_rate_hz"] == 22050
    assert abs(data["duration_ms"] - 500.0) <= 1.0
    assert base64.b64decode(data["audio_base64"]) == original


def test_health_reports_active_tts_engine(
    production_tts: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """The health route names the active speech synthesis engine once the binary answers."""
    script = tmp_path / "espeak-ng-version"
    script.write_text("#!/bin/sh\necho 'eSpeak NG stub'\nexit 0\n", encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setenv("RUNEFOBLE_VOICE_TTS_BINARY", str(script))

    resp = TestClient(app, headers=voice_auth_headers()).get("/healthz")

    assert resp.status_code == 200, resp.text
    assert resp.json()["tts_engine"] == "espeak-ng"


def _pcm_b64() -> str:
    return base64.b64encode(generate_pcm_sine(duration_ms=100)).decode("ascii")
