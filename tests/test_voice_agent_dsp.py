"""Tests for Voice Agent DSP audio conditioning and speech slur engine."""

import time

from fastapi.testclient import TestClient
from voice_agent.dsp import VoiceDSPPipeline
from voice_agent.main import app

client = TestClient(app)


def test_dsp_text_slurring():
    """Verify phonetic slurs and hiccup insertions for inebriated speech."""
    pipeline = VoiceDSPPipeline()
    text = "Stand firm, companions! The goblins are attacking from the east!"
    processed = pipeline.process(text, filters=["drunk"])

    assert processed.original_text == text
    assert processed.conditioned_text != text
    # Should include hiccup
    assert "*hic!*" in processed.conditioned_text
    # Should have high slur intensity
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
    # 1. Synthesize with drunk filter
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

    # 2. Synthesize with backward-compatible apply_drunk_filter
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
