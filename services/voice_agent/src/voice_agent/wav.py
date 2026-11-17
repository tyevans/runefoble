"""PCM WAV encoding and decoding for synthesised audio."""

from __future__ import annotations

import io
import wave

from voice_agent.synthesizer import AudioClip


def encode_wav(clip: AudioClip) -> bytes:
    """Wrap an audio clip in a RIFF/WAVE container (mono, 16-bit PCM)."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(clip.sample_rate)
        wf.writeframes(clip.pcm)
    return buffer.getvalue()


def decode_wav(data: bytes) -> AudioClip:
    """Read a mono 16-bit PCM WAV container. Raises ValueError for any other format."""
    try:
        with wave.open(io.BytesIO(data), "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            sample_rate = wf.getframerate()
            pcm = wf.readframes(wf.getnframes())
    except (wave.Error, EOFError) as exc:
        raise ValueError(f"not a WAV container: {exc}") from exc
    if channels != 1 or sample_width != 2:
        raise ValueError(
            f"expected mono 16-bit PCM, got {channels} channel(s) at {sample_width} byte(s)"
        )
    return AudioClip(pcm=pcm, sample_rate=sample_rate)
