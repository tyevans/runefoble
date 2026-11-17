"""PCM Audio Buffer Utilities.

Normalizes audio inputs into signed 16-bit PCM arrays.
"""

from __future__ import annotations

import array


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
