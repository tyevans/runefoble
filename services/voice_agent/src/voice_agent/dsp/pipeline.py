"""Low-latency PCM Stream Pipeline Filter for WebRTC Audio Streaming."""

from __future__ import annotations

import array
import time
from typing import Any

from voice_agent.audio_utils import to_samples_array
from voice_agent.dsp.formants import shift_pitch_and_formants
from voice_agent.dsp.presets import NPCVoicePreset, get_preset


class StreamPipelineFilter:
    """Low-latency PCM stream filter hooked into WebRTC audio track streaming.

    Applies pitch scaling, formant shifting, and resonance filters with <50ms processing latency.
    """

    def __init__(self, preset: NPCVoicePreset | str | None = None):
        self.preset: NPCVoicePreset | None = (
            get_preset(preset) if isinstance(preset, str) else preset
        )
        self.pitch_shift_semitones: float | None = None
        self.formant_shift: float | None = None
        self.resonance_hz: float | None = None
        self.octave_offset: float | None = None
        self.enabled: bool = True

    def set_preset(self, preset: NPCVoicePreset | str | None) -> None:
        """Activate an NPC vocal archetype preset or clear it."""
        if isinstance(preset, str):
            self.preset = get_preset(preset)
        else:
            self.preset = preset

    def configure(
        self,
        pitch_shift_semitones: float | None = None,
        formant_shift: float | None = None,
        resonance_hz: float | None = None,
        octave_offset: float | None = None,
        enabled: bool | None = None,
    ) -> None:
        """Fine-tune DSP parameters and overrides."""
        if pitch_shift_semitones is not None:
            self.pitch_shift_semitones = pitch_shift_semitones
        if formant_shift is not None:
            self.formant_shift = formant_shift
        if resonance_hz is not None:
            self.resonance_hz = resonance_hz
        if octave_offset is not None:
            self.octave_offset = octave_offset
        if enabled is not None:
            self.enabled = enabled

    def process_frame(
        self,
        pcm_bytes: bytes | array.array,
        sample_rate: int = 16000,
    ) -> tuple[bytes, dict[str, Any], float]:
        """Process an incoming PCM frame with low latency (<50ms).

        Returns:
            Tuple of (processed_pcm_bytes, metadata_dict, latency_ms).
        """
        start = time.perf_counter()
        raw_arr = to_samples_array(pcm_bytes)
        raw_bytes = raw_arr.tobytes()

        has_override = any(
            v is not None
            for v in (
                self.pitch_shift_semitones,
                self.formant_shift,
                self.resonance_hz,
                self.octave_offset,
            )
        )
        if not self.enabled or (self.preset is None and not has_override):
            latency = (time.perf_counter() - start) * 1000.0
            return raw_bytes, {"bypassed": True, "latency_ms": round(latency, 3)}, latency

        p = self.preset
        pitch = (
            self.pitch_shift_semitones
            if self.pitch_shift_semitones is not None
            else (p.pitch_shift_semitones if p else 0.0)
        )
        formant = (
            self.formant_shift
            if self.formant_shift is not None
            else (p.formant_shift if p else 1.0)
        )
        resonance = (
            self.resonance_hz if self.resonance_hz is not None else (p.resonance_hz if p else 0.0)
        )
        octave = (
            self.octave_offset
            if self.octave_offset is not None
            else (p.octave_offset if p else 0.0)
        )
        reverb = p.reverb_wet if p else 0.0
        ring_mod = p.ring_mod_hz if p else 0.0
        gain_db = p.gain_db if p else 0.0

        processed = shift_pitch_and_formants(
            raw_arr,
            sample_rate=sample_rate,
            pitch_shift_semitones=pitch,
            formant_shift=formant,
            resonance_hz=resonance,
            octave_offset=octave,
            ring_mod_hz=ring_mod,
            reverb_wet=reverb,
            gain_db=gain_db,
        )
        out_bytes = processed.tobytes()
        latency_ms = (time.perf_counter() - start) * 1000.0

        meta = {
            "preset": p.preset_id if p else "custom",
            "pitch_shift_semitones": pitch,
            "formant_shift": formant,
            "resonance_hz": resonance,
            "octave_offset": octave,
            "active_filters": list(p.active_filters) if p else [],
            "latency_ms": round(latency_ms, 3),
        }
        return out_bytes, meta, latency_ms


__all__ = ["StreamPipelineFilter"]
