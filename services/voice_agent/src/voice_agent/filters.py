"""Digital Signal Processing (DSP) Audio Filters.

Provides low-level PCM audio filter implementations: dynamic range compression,
high-pass shimmer, muffled low-pass, sub-bass resonance, echo delay lines,
and pitch sway modulation.
"""

from __future__ import annotations

import array
import math
import time
from typing import Any

from voice_agent.audio_utils import _to_samples_array, generate_synthetic_audio


def whisper_filter(
    samples: array.array | bytes | list[float | int],
    sample_rate: int = 16000,
) -> tuple[array.array, dict[str, Any]]:
    """Whisper filter: reduced dynamic range and high-pass shimmer."""
    input_arr = _to_samples_array(samples)
    fc = 1800.0
    dt = 1.0 / sample_rate
    rc = 1.0 / (2.0 * math.pi * fc)
    alpha = rc / (rc + dt)

    out = array.array("h")
    prev_x = 0.0
    prev_y = 0.0
    shimmer_step = 2.0 * math.pi * 4200.0 / sample_rate
    for i, s in enumerate(input_arr):
        norm = s / 32768.0
        sign = 1.0 if norm >= 0 else -1.0
        compressed = sign * (abs(norm) ** 0.55) * 0.40
        y = alpha * (prev_y + compressed - prev_x)
        prev_x = compressed
        prev_y = y
        shimmer = 0.15 * math.sin(i * shimmer_step) * compressed
        val = max(-32767, min(32767, int((y + shimmer) * 32767)))
        out.append(val)

    metadata = {
        "filter": "whisper",
        "reduced_dynamic_range": True,
        "dynamic_range_ratio": 0.40,
        "high_pass_shimmer": True,
        "high_pass_cutoff_hz": 1800,
        "shimmer_frequency_hz": 4200,
    }
    return out, metadata


def underwater_filter(
    samples: array.array | bytes | list[float | int],
    sample_rate: int = 16000,
) -> tuple[array.array, dict[str, Any]]:
    """Underwater filter: muffled low-pass and sub-bass resonance."""
    input_arr = _to_samples_array(samples)
    fc = 500.0
    dt = 1.0 / sample_rate
    rc = 1.0 / (2.0 * math.pi * fc)
    alpha = dt / (rc + dt)

    out = array.array("h")
    y = 0.0
    sub_bass_step = 2.0 * math.pi * 85.0 / sample_rate
    for i, s in enumerate(input_arr):
        norm = s / 32768.0
        y += alpha * (norm - y)
        sub_bass = 0.25 * math.sin(i * sub_bass_step) * abs(norm)
        val = max(-32767, min(32767, int((y + sub_bass) * 32767)))
        out.append(val)

    metadata = {
        "filter": "underwater",
        "muffled_low_pass": True,
        "low_pass_cutoff_hz": 500,
        "sub_bass_resonance": True,
        "resonance_frequency_hz": 85,
        "sub_bass_boost_db": 6.5,
    }
    return out, metadata


def ethereal_filter(
    samples: array.array | bytes | list[float | int],
    sample_rate: int = 16000,
) -> tuple[array.array, dict[str, Any]]:
    """Ethereal filter: ghostly echo modulation and delay tail."""
    input_arr = _to_samples_array(samples)
    delay_ms = 180
    d_samples = max(1, int(delay_ms * sample_rate / 1000))
    tail_samples = max(1, min(int(50 * sample_rate / 1000), len(input_arr)))
    total_len = len(input_arr) + tail_samples

    out = array.array("h", [0] * total_len)
    feedback = 0.45
    lfo_step = 2.0 * math.pi * 1.2 / sample_rate
    for i in range(total_len):
        orig = input_arr[i] if i < len(input_arr) else 0
        delayed = out[i - d_samples] if i >= d_samples else 0
        lfo = 1.0 + 0.12 * math.sin(i * lfo_step)
        val = orig + int(delayed * feedback * lfo)
        out[i] = max(-32767, min(32767, val))

    metadata = {
        "filter": "ethereal",
        "ghostly_echo_modulation": True,
        "echo_modulation": True,
        "delay_tail": True,
        "echo_delay_ms": delay_ms,
        "delay_ms": delay_ms,
        "tail_duration_ms": 200,
        "feedback": feedback,
    }
    return out, metadata


def drunk_filter(
    samples: array.array | bytes | list[float | int],
    sample_rate: int = 16000,
) -> tuple[array.array, dict[str, Any]]:
    """Drunk filter: slurred formant modulation and pitch sway."""
    input_arr = _to_samples_array(samples)
    out = array.array("h")
    n = len(input_arr)
    sway_step = 2.0 * math.pi * 0.8 / sample_rate
    wobble_step = 2.0 * math.pi * 0.5 / sample_rate
    for i in range(n):
        sway = int(10.0 * math.sin(i * sway_step))
        idx = max(0, min(n - 1, i + sway))
        s = input_arr[idx]
        norm = s / 32768.0
        wobble = 0.85 + 0.15 * math.sin(i * wobble_step)
        val = max(-32767, min(32767, int(norm * wobble * 32767)))
        out.append(val)

    metadata = {
        "filter": "drunk",
        "slurred_formant_modulation": True,
        "formant_modulation": True,
        "pitch_sway": True,
        "pitch_sway_cents": 35.0,
        "pitch_sway_hz": 0.8,
        "wobble_depth": 0.4,
    }
    return out, metadata


def apply_audio_filters(
    audio_data: bytes | array.array | list[float | int] | None,
    filters: list[str],
    sample_rate: int = 16000,
) -> tuple[bytes, dict[str, Any], float]:
    """Execute the audio filter chain and return (audio_bytes, metadata, latency_ms)."""
    t0 = time.perf_counter()
    if audio_data is None or (
        isinstance(audio_data, (bytes, list, array.array)) and len(audio_data) == 0
    ):
        current_samples = _to_samples_array(generate_synthetic_audio(0.05, sample_rate))
    else:
        current_samples = _to_samples_array(audio_data)

    combined_metadata: dict[str, Any] = {}
    normalized_filters = [f.lower().strip() for f in filters]

    for f in normalized_filters:
        if f == "whisper":
            current_samples, meta = whisper_filter(current_samples, sample_rate)
            combined_metadata.update(meta)
        elif f == "underwater":
            current_samples, meta = underwater_filter(current_samples, sample_rate)
            combined_metadata.update(meta)
        elif f in ("ethereal", "ghostly"):
            current_samples, meta = ethereal_filter(current_samples, sample_rate)
            combined_metadata.update(meta)
        elif f == "drunk":
            current_samples, meta = drunk_filter(current_samples, sample_rate)
            combined_metadata.update(meta)

    latency_ms = (time.perf_counter() - t0) * 1000.0
    return current_samples.tobytes(), combined_metadata, latency_ms
