"""PCM Audio Buffer Utilities and Waveform Generators.

Normalizes audio inputs into signed 16-bit PCM arrays and generates synthetic
speech carrier waveforms with rich voice harmonics.
"""

from __future__ import annotations

import array
import math

_cached_synthetic_audio: dict[tuple[float, int], bytes] = {}


def to_samples_array(
    samples: array.array | bytes | bytearray | list[float | int],
) -> array.array:
    """Normalize various input formats into a signed 16-bit PCM array."""
    if isinstance(samples, array.array):
        if samples.typecode == "h":
            return array.array("h", samples)
        return array.array(
            "h",
            [
                max(-32767, min(32767, int(s * 32767 if isinstance(s, float) else s)))
                for s in samples
            ],
        )
    if isinstance(samples, (bytes, bytearray)):
        pcm_bytes = samples[44:] if samples.startswith(b"RIFF") else bytes(samples)
        if len(pcm_bytes) % 2 != 0:
            pcm_bytes = pcm_bytes[:-1]
        arr = array.array("h")
        arr.frombytes(pcm_bytes)
        return arr
    if isinstance(samples, list):
        if samples and isinstance(samples[0], float):
            return array.array("h", [max(-32767, min(32767, int(s * 32767))) for s in samples])
        return array.array("h", [max(-32767, min(32767, int(s))) for s in samples])
    return array.array("h")


def _to_samples_array(
    samples: array.array | bytes | bytearray | list[float | int],
) -> array.array:
    """Backward-compatible private alias for to_samples_array."""
    return to_samples_array(samples)


def generate_synthetic_audio(duration_sec: float = 0.05, sample_rate: int = 16000) -> bytes:
    """Generate a clean synthetic speech carrier waveform (rich voice harmonics)."""
    key = (duration_sec, sample_rate)
    if key in _cached_synthetic_audio:
        return _cached_synthetic_audio[key]

    n_samples = max(160, int(duration_sec * sample_rate))
    samples = array.array("h")
    f0 = 220.0
    omega = 2.0 * math.pi * f0 / sample_rate
    fade_len = int(0.01 * sample_rate)
    for i in range(n_samples):
        theta = i * omega
        val = (
            0.50 * math.sin(theta)
            + 0.25 * math.sin(2 * theta)
            + 0.15 * math.sin(3 * theta)
            + 0.10 * math.sin(4 * theta)
        )
        fade = min(1.0, i / max(1, fade_len), (n_samples - 1 - i) / max(1, fade_len))
        clamped = max(-32767, min(32767, int(val * fade * 20000)))
        samples.append(clamped)
    raw = samples.tobytes()
    _cached_synthetic_audio[key] = raw
    return raw
