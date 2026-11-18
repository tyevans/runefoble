"""Tests for Voice Agent DSP audio conditioning and speech slur engine."""

from __future__ import annotations

import asyncio
import time

import pytest
from fastapi.testclient import TestClient
from voice_agent.audio_utils import to_samples_array
from voice_agent.dsp import (
    DSPFilterConfig,
    ProcessedSpeechResult,
    VoiceDSPPipeline,
    apply_audio_filters,
    drunk_filter,
    ethereal_filter,
    underwater_filter,
    whisper_filter,
)
from voice_agent.main import app
from voice_agent.phonetics import (
    apply_slurred_speech,
    apply_text_transforms,
    slur_phonemes,
)
from voice_agent.room import VoiceRoomAggregate, VoiceRoomState

from tests.helpers.audio_synth import generate_synthetic_audio
from tests.helpers.spicedb_factory import grant_voice_session
from tests.helpers.voice_identity import voice_auth_headers


@pytest.fixture(autouse=True)
def _voice_session_grants() -> None:
    """Make the DM and the speakers of these literal sessions authorized through the SpiceDB seam."""
    for session_id in (
        "session_default",
        "sess-1",
    ):
        asyncio.run(grant_voice_session(session_id, players=["speaker_default"]))


pytestmark = pytest.mark.usefixtures("trusted_voice_issuer", "fake_speech_synthesizer")

client = TestClient(app, headers=voice_auth_headers())


def test_dsp_text_slurring():
    """Verify phonetic slurs and hiccup insertions for inebriated speech."""
    pipeline = VoiceDSPPipeline()
    text = "Stand firm, companions! The goblins are attacking from the east!"
    processed = pipeline.process(text, filters=["drunk"])

    assert processed.original_text == text
    assert processed.conditioned_text != text
    assert "*hic!*" in processed.conditioned_text
    assert processed.dsp_config.slur_intensity >= 0.7
    assert processed.dsp_config.vibrato_depth > 0.0


def test_dsp_whisper_and_underwater():
    """Test acoustic filters for whisper and underwater environments."""
    pipeline = VoiceDSPPipeline()

    whisper = pipeline.process("Keep your heads down.", filters=["whisper"])
    assert "*whispers*" in whisper.conditioned_text
    assert whisper.dsp_config.low_pass_cutoff_hz == 3200

    underwater = pipeline.process("Help me!", filters=["underwater"])
    assert "*blub*" in underwater.conditioned_text
    assert underwater.dsp_config.low_pass_cutoff_hz == 800
    assert underwater.dsp_config.reverb_wet >= 0.6


def test_dsp_pipeline_latency():
    """Verify sub-50ms processing speed for DSP transforms."""
    pipeline = VoiceDSPPipeline()
    sample = "The ancient dragon exhales a searing blast of brimstone across the tactical grid!"

    start = time.perf_counter()
    for _ in range(50):
        pipeline.process(sample, filters=["drunk", "ghostly"])
    elapsed = (time.perf_counter() - start) / 50

    assert elapsed < 0.05, f"DSP pipeline took too long: {elapsed * 1000:.2f}ms"


def test_voice_tts_endpoints():
    """Test FastAPI TTS endpoints with affliction filters."""
    res = client.post(
        "/api/v1/voice/tts",
        json={
            "text": "I charge forward with sword held high!",
            "persona_id": "valeros_fighter",
            "filters": ["drunk"],
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "drunk" in data["effects_applied"]
    assert "*hic!*" in data["conditioned_text"]
    assert "pitch_shift_semitones" in data["dsp_parameters"]

    res2 = client.post(
        "/api/v1/voice/synthesize",
        json={
            "text": "Glory awaits!",
            "persona_id": "kyra_stand_in",
            "apply_drunk_filter": True,
        },
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert "drunk" in data2["effects_applied"]


def test_modular_phonetics_and_filters():
    """Verify isolated modular phonetics and low-level filters."""
    text = "The castle guards approach."
    slurred = apply_slurred_speech(text)
    assert "*hic!*" in slurred
    assert slur_phonemes(text) == slurred

    transformed = apply_text_transforms("Hello", ["underwater", "whisper"])
    assert "*blub*" in transformed
    assert "*whispers*" in transformed

    raw = generate_synthetic_audio(0.02, 16000)
    samples = to_samples_array(raw)
    assert len(samples) > 0

    w_out, w_meta = whisper_filter(samples, 16000)
    assert w_meta["filter"] == "whisper"
    u_out, u_meta = underwater_filter(samples, 16000)
    assert u_meta["filter"] == "underwater"
    e_out, e_meta = ethereal_filter(samples, 16000)
    assert e_meta["filter"] == "ethereal"
    d_out, d_meta = drunk_filter(samples, 16000)
    assert d_meta["filter"] == "drunk"


def test_backward_compatible_reexports():
    """Verify backward-compatible re-exports from voice_agent.dsp and voice_agent.room."""
    cfg = DSPFilterConfig()
    assert cfg.speed_factor == 1.0
    res = ProcessedSpeechResult(original_text="hello", conditioned_text="hello", dsp_config=cfg)
    assert res.original_text == "hello"
    audio_bytes, _, _ = apply_audio_filters(generate_synthetic_audio(0.05, 16000), ["whisper"])
    assert len(audio_bytes) > 0
    state = VoiceRoomState(session_id="sess-1")
    assert state.active is True
    agg = VoiceRoomAggregate("00000000-0000-0000-0000-000000000001")
    assert agg.aggregate_type == "VoiceRoom"
