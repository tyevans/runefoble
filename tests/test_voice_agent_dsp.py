"""Tests for Voice Agent DSP audio conditioning and speech slur engine."""

from __future__ import annotations

import pathlib
import time

from fastapi.testclient import TestClient
from voice_agent.audio_utils import generate_synthetic_audio, to_samples_array
from voice_agent.coordinator import VoiceRoomCoordinator, get_voice_room_coordinator
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
from voice_agent.routers import (
    audio_router,
    room_router,
    stream_router,
    synthesis_router,
)

client = TestClient(app)


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


def test_modular_room_and_routers():
    """Verify modular router mounting and room coordinator architecture."""
    assert audio_router is not None
    assert synthesis_router is not None
    assert room_router is not None
    assert stream_router is not None

    coord = get_voice_room_coordinator()
    assert isinstance(coord, VoiceRoomCoordinator)

    # Invariant: modified and new source files < 200 lines
    va_dir = pathlib.Path(__file__).parent.parent / "services/voice_agent/src/voice_agent"
    for py_file in va_dir.glob("*.py"):
        if py_file.name in ("stt.py", "vad.py"):
            continue
        line_count = len(py_file.read_text(encoding="utf-8").splitlines())
        assert line_count < 200, f"{py_file.name} exceeded 200 lines ({line_count})"

    for router_file in (va_dir / "routers").glob("*.py"):
        line_count = len(router_file.read_text(encoding="utf-8").splitlines())
        assert line_count < 200, f"{router_file.name} exceeded 200 lines ({line_count})"


def test_backward_compatible_reexports():
    """Verify backward-compatible re-exports from voice_agent.dsp and voice_agent.room."""
    cfg = DSPFilterConfig()
    assert cfg.speed_factor == 1.0
    res = ProcessedSpeechResult(original_text="hello", conditioned_text="hello", dsp_config=cfg)
    assert res.original_text == "hello"
    audio_bytes, _, _ = apply_audio_filters(None, ["whisper"])
    assert len(audio_bytes) > 0
    state = VoiceRoomState(session_id="sess-1")
    assert state.active is True
    agg = VoiceRoomAggregate("00000000-0000-0000-0000-000000000001")
    assert agg.aggregate_type == "VoiceRoom"
