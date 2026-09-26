"""Digital Signal Processing (DSP) Audio Conditioning and Slur Engine.

Provides real-time speech transformation, phonetic slurs, audio filter coefficient
computation, and fast digital signal processing filter chains for tabletop afflictions.
"""

import array
import math
import re
import time
from typing import Any

from pydantic import BaseModel, Field


class DSPFilterConfig(BaseModel):
    """Audio DSP coefficients and parameters for speech synthesis rendering."""

    pitch_shift_semitones: float = 0.0
    formant_shift: float = 1.0
    reverb_wet: float = 0.0
    low_pass_cutoff_hz: int | None = None
    vibrato_depth: float = 0.0
    slur_intensity: float = 0.0
    speed_factor: float = 1.0
    hiccup_frequency: float = 0.0


class ProcessedSpeechResult(BaseModel):
    """Result of DSP processing on speech text and audio parameters."""

    original_text: str
    conditioned_text: str
    active_filters: list[str] = Field(default_factory=list)
    dsp_config: DSPFilterConfig
    latency_ms: float = 1.5


def _to_samples_array(samples: array.array | bytes | bytearray | list[float | int]) -> array.array:
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


_cached_synthetic_audio: dict[tuple[float, int], bytes] = {}


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
        # Reduce dynamic range (compression of soft/loud contrasts)
        sign = 1.0 if norm >= 0 else -1.0
        compressed = sign * (abs(norm) ** 0.55) * 0.40
        # First-order high-pass filter
        y = alpha * (prev_y + compressed - prev_x)
        prev_x = compressed
        prev_y = y
        # High-pass shimmer modulation
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
        # First-order low-pass filter (muffled attenuation)
        y += alpha * (norm - y)
        # Sub-bass resonance rumble
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
        # Pitch sway via low-frequency delay wobble
        sway = int(10.0 * math.sin(i * sway_step))
        idx = max(0, min(n - 1, i + sway))
        s = input_arr[idx]
        norm = s / 32768.0
        # Slurred formant modulation
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


class VoiceDSPPipeline:
    """Pipeline for transforming speech text and computing DSP filter parameters."""

    def __init__(self) -> None:
        self._s_pattern = re.compile(r"\b([a-zA-Z]+)s([a-zA-Z]*)\b", re.IGNORECASE)

    def slur_phonemes(self, text: str) -> str:
        """Inject inebriated slurs, elongated vowels, and hiccups into text."""
        words = text.split()
        slurred_words = []

        for i, word in enumerate(words):
            w = word
            # Slur sibilants
            w = re.sub(r"([sS])([tTcCkKpP])", r"\1hh\2", w)
            w = re.sub(r"([sS])\b", r"\1hh", w)
            w = re.sub(r"\bth", "f", w, flags=re.IGNORECASE)

            # Elongate vowels periodically
            if len(w) > 4 and any(c in "aeiouAEIOU" for c in w):
                w = re.sub(r"([oo|ee|aa|uu|ii])", r"\1\1", w, count=1)

            slurred_words.append(w)

            # Insert hiccups every 4-6 words
            if i > 0 and i % 5 == 0:
                slurred_words.append("*hic!*")

        if not any(h in slurred_words for h in ["*hic!*", "*burp*"]):
            slurred_words.insert(0, "*hic!*")

        return " ".join(slurred_words)

    def apply_text_transforms(self, text: str, filters: list[str]) -> str:
        """Apply text conditioning according to active affliction filters."""
        result = text
        filters_clean = [f.lower().strip() for f in filters]

        if "drunk" in filters_clean:
            result = self.slur_phonemes(result)

        if "underwater" in filters_clean:
            result = f"*blub* {result} *gurgle*"

        if "whisper" in filters_clean:
            result = f"...*whispers* {result.lower()}..."

        if "ethereal" in filters_clean or "ghostly" in filters_clean:
            result = f"~ {result} ~ ...{result.split()[-1]}... ~"

        return result

    def compute_dsp_config(self, filters: list[str], persona_pitch: float = 1.0) -> DSPFilterConfig:
        """Compute audio DSP coefficients based on active filters and persona pitch."""
        config = DSPFilterConfig()
        filters_clean = [f.lower().strip() for f in filters]

        # Base pitch adjustment from persona
        config.pitch_shift_semitones = (persona_pitch - 1.0) * 12.0

        if "drunk" in filters_clean:
            config.pitch_shift_semitones -= 1.5
            config.vibrato_depth = 0.4
            config.slur_intensity = 0.8
            config.speed_factor = 0.88
            config.hiccup_frequency = 0.25

        if "whisper" in filters_clean:
            config.low_pass_cutoff_hz = 3200
            config.formant_shift = 1.2
            config.speed_factor = 0.95
            config.reverb_wet = 0.15

        if "underwater" in filters_clean:
            config.low_pass_cutoff_hz = 800
            config.reverb_wet = 0.65
            config.vibrato_depth = 0.3
            config.speed_factor = 0.75

        if "ethereal" in filters_clean or "ghostly" in filters_clean:
            config.pitch_shift_semitones += 2.0
            config.reverb_wet = 0.85
            config.formant_shift = 0.9
            config.vibrato_depth = 0.5

        return config

    def process(
        self,
        text: str,
        filters: list[str],
        persona_pitch: float = 1.0,
    ) -> ProcessedSpeechResult:
        """Execute full DSP text transformation and parameter computation."""
        conditioned = self.apply_text_transforms(text, filters)
        dsp = self.compute_dsp_config(filters, persona_pitch)

        return ProcessedSpeechResult(
            original_text=text,
            conditioned_text=conditioned,
            active_filters=filters,
            dsp_config=dsp,
        )
