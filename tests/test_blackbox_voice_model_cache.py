"""Blackbox tests for voice agent readiness and the speech assets it needs (TASK-0676).

The readiness check runs through the public `GET /healthz` route. The tests set
configuration (environment variables) and the filesystem state of the model cache
and the speech binary. They do not patch private state.
"""

from __future__ import annotations

import shutil
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from voice_agent.main import app

from tests.helpers.audio_synth import build_speech_seams_from_env, keep_speech_seams
from tests.helpers.module_state import SeamRestorer
from tests.helpers.voice_identity import voice_auth_headers

pytestmark = pytest.mark.usefixtures("trusted_voice_issuer")

MODEL_SIZE = "tiny.en"
MODEL_REPO_DIR = f"models--Systran--faster-whisper-{MODEL_SIZE}"


def _cache_model(model_dir: Path) -> Path:
    """Lay out one cached model the way the Hugging Face cache does."""
    snapshot = model_dir / MODEL_REPO_DIR / "snapshots" / "0" / "model.bin"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_bytes(b"model")
    return snapshot


@pytest.fixture
def espeak_stub(tmp_path: Path) -> Path:
    """A process-boundary stand-in for the espeak-ng binary. It reports a version and exits 0."""
    stub = tmp_path / "bin" / "espeak-ng"
    stub.parent.mkdir()
    stub.write_text("#!/bin/sh\necho 'eSpeak NG stub'\nexit 0\n", encoding="utf-8")
    stub.chmod(0o755)
    return stub


@pytest.fixture
def model_dir(tmp_path: Path) -> Path:
    path = tmp_path / "whisper"
    path.mkdir()
    return path


@pytest.fixture
def speech_env(
    monkeypatch: pytest.MonkeyPatch,
    espeak_stub: Path,
    model_dir: Path,
    seam_restorer: SeamRestorer,
) -> Generator[None]:
    """Configure the voice agent with the stub binary and a model cache, download disabled."""
    keep_speech_seams(seam_restorer)
    monkeypatch.setenv("RUNEFOBLE_VOICE_TTS_BINARY", str(espeak_stub))
    monkeypatch.setenv("RUNEFOBLE_VOICE_STT_MODEL_SIZE", MODEL_SIZE)
    monkeypatch.setenv("RUNEFOBLE_VOICE_STT_MODEL_DIR", str(model_dir))
    monkeypatch.setenv("RUNEFOBLE_VOICE_STT_DOWNLOAD_ENABLED", "false")
    build_speech_seams_from_env()
    yield


def test_health_is_ready_with_speech_binary_and_cached_model(speech_env: None, model_dir: Path):
    """With the binary present and the model cached, the health route reports ready."""
    _cache_model(model_dir)

    resp = TestClient(app, headers=voice_auth_headers()).get("/healthz")

    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ok"


def test_health_is_not_ready_when_model_cache_is_removed(speech_env: None, model_dir: Path):
    """Removing the cached model flips the health route to not-ready. No silent fallback."""
    _cache_model(model_dir)
    client = TestClient(app, headers=voice_auth_headers())
    assert client.get("/healthz").status_code == 200

    shutil.rmtree(model_dir / MODEL_REPO_DIR)

    resp = client.get("/healthz")
    assert resp.status_code == 503, resp.text
    body = resp.json()
    assert body["status"] == "not_ready"
    assert "stt" in body["problems"]
    assert MODEL_SIZE in body["problems"]["stt"]


def test_health_is_not_ready_when_model_cache_is_empty_and_download_disabled(
    speech_env: None,
):
    """An empty model directory with download disabled is not ready."""
    resp = TestClient(app, headers=voice_auth_headers()).get("/healthz")

    assert resp.status_code == 503, resp.text
    assert "stt" in resp.json()["problems"]


def test_health_is_ready_when_download_is_enabled_and_cache_is_empty(
    speech_env: None, monkeypatch: pytest.MonkeyPatch
):
    """Local development may download the model on first use, so an empty cache is ready."""
    monkeypatch.setenv("RUNEFOBLE_VOICE_STT_DOWNLOAD_ENABLED", "true")
    build_speech_seams_from_env()

    resp = TestClient(app, headers=voice_auth_headers()).get("/healthz")

    assert resp.status_code == 200, resp.text


def test_health_is_not_ready_when_speech_binary_is_missing(
    speech_env: None, model_dir: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """A missing espeak-ng binary fails the readiness check. It does not degrade silently."""
    _cache_model(model_dir)
    monkeypatch.setenv("RUNEFOBLE_VOICE_TTS_BINARY", str(tmp_path / "absent" / "espeak-ng"))
    build_speech_seams_from_env()

    resp = TestClient(app, headers=voice_auth_headers()).get("/healthz")

    assert resp.status_code == 503, resp.text
    body = resp.json()
    assert body["status"] == "not_ready"
    assert "tts" in body["problems"]


def test_health_is_not_ready_when_speech_binary_version_check_fails(
    speech_env: None, model_dir: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """A binary that exits with an error on `--version` fails the readiness check."""
    _cache_model(model_dir)
    broken = tmp_path / "bin-broken" / "espeak-ng"
    broken.parent.mkdir()
    broken.write_text("#!/bin/sh\necho 'no audio device' >&2\nexit 3\n", encoding="utf-8")
    broken.chmod(0o755)
    monkeypatch.setenv("RUNEFOBLE_VOICE_TTS_BINARY", str(broken))
    build_speech_seams_from_env()

    resp = TestClient(app, headers=voice_auth_headers()).get("/healthz")

    assert resp.status_code == 503, resp.text
    assert "tts" in resp.json()["problems"]
