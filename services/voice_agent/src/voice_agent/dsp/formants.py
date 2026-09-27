"""Formant scaling, resonance frequency shifting, and pitch octave offsets DSP nodes."""

from __future__ import annotations

import array
import math

from voice_agent.audio_utils import to_samples_array


def biquad_resonance(
    samples: array.array, sample_rate: int, freq_hz: float, gain_db: float = 6.0, q: float = 2.0
) -> array.array:
    """Apply a 2nd-order biquad peaking filter for vocal tract resonance."""
    freq = max(20.0, min(sample_rate * 0.45, float(freq_hz)))
    w0 = 2.0 * math.pi * freq / sample_rate
    alpha = math.sin(w0) / (2.0 * max(0.1, q))
    A = 10.0 ** (gain_db / 40.0)
    b0, b1, b2 = 1.0 + alpha * A, -2.0 * math.cos(w0), 1.0 - alpha * A
    a0, a1, a2 = 1.0 + alpha / A, -2.0 * math.cos(w0), 1.0 - alpha / A

    out = array.array("h")
    x1 = x2 = y1 = y2 = 0.0
    for s in samples:
        x0 = float(s)
        y0 = (b0 / a0) * x0 + (b1 / a0) * x1 + (b2 / a0) * x2 - (a1 / a0) * y1 - (a2 / a0) * y2
        x2, x1, y2, y1 = x1, x0, y1, y0
        out.append(max(-32767, min(32767, int(y0))))
    return out


def pitch_shift(
    samples: array.array, sample_rate: int, semitones: float, window_sec: float = 0.03
) -> array.array:
    """Real-time dual-tap delay crossfade pitch shifter node (WebAudio model)."""
    if abs(semitones) < 0.05 or len(samples) < 32:
        return array.array("h", samples)

    ratio = 2.0 ** (semitones / 12.0)
    win_len = max(64, int(window_sec * sample_rate))
    delta = (1.0 - ratio) / win_len
    out = array.array("h")
    n = len(samples)
    phase = 0.0

    for i in range(n):
        phase = (phase + delta) % 1.0
        d1 = phase * win_len
        d2 = ((phase + 0.5) % 1.0) * win_len
        w1 = 0.5 - 0.5 * math.cos(2.0 * math.pi * phase)
        w2 = 1.0 - w1

        i1 = max(0, min(n - 1, int(i - d1)))
        i2 = max(0, min(n - 1, int(i - d2)))
        v = w1 * samples[i1] + w2 * samples[i2]
        out.append(max(-32767, min(32767, int(v))))
    return out


def shift_pitch_and_formants(
    samples: array.array | bytes | list[float | int],
    sample_rate: int = 16000,
    pitch_shift_semitones: float = 0.0,
    formant_shift: float = 1.0,
    resonance_hz: float = 0.0,
    octave_offset: float = 0.0,
    ring_mod_hz: float = 0.0,
    reverb_wet: float = 0.0,
    gain_db: float = 0.0,
) -> array.array:
    """Execute DSP filter chain for formant manipulation, pitch scaling, and resonances."""
    arr = to_samples_array(samples)
    if not arr:
        return array.array("h")

    # 1. Total pitch offset (semitones + octave offset)
    total_semitones = pitch_shift_semitones + (octave_offset * 12.0)
    if abs(total_semitones) >= 0.05:
        arr = pitch_shift(arr, sample_rate, total_semitones)

    # 2. Formant scaling via spectral envelope pole shifting
    if abs(formant_shift - 1.0) >= 0.05:
        # Scale nominal vocal formants (F1: 600Hz, F2: 1800Hz)
        f1_target = min(sample_rate * 0.45, max(120.0, 600.0 * formant_shift))
        f2_target = min(sample_rate * 0.45, max(300.0, 1800.0 * formant_shift))
        gain1 = 4.0 if formant_shift < 1.0 else -3.0
        gain2 = -4.0 if formant_shift < 1.0 else 5.0
        arr = biquad_resonance(arr, sample_rate, f1_target, gain_db=gain1, q=1.8)
        arr = biquad_resonance(arr, sample_rate, f2_target, gain_db=gain2, q=2.2)

    # 3. Dedicated creature resonance frequency boost
    if resonance_hz > 20.0:
        arr = biquad_resonance(arr, sample_rate, resonance_hz, gain_db=gain_db or 5.0, q=2.5)

    # 4. Ring modulation (robotic / digitized carrier)
    if ring_mod_hz > 0.0:
        mod = array.array("h")
        omega = 2.0 * math.pi * ring_mod_hz / sample_rate
        for i, s in enumerate(arr):
            carrier = 0.35 + 0.65 * math.sin(i * omega)
            mod.append(max(-32767, min(32767, int(s * carrier))))
        arr = mod

    # 5. Ethereal / cavernous reverb reflection
    if reverb_wet > 0.05:
        rev = array.array("h")
        del1 = int(0.023 * sample_rate)
        del2 = int(0.037 * sample_rate)
        dry = 1.0 - (reverb_wet * 0.4)
        for i in range(len(arr)):
            s0 = float(arr[i])
            r1 = float(arr[i - del1]) if i >= del1 else 0.0
            r2 = float(arr[i - del2]) if i >= del2 else 0.0
            val = (dry * s0) + (reverb_wet * (0.6 * r1 + 0.4 * r2))
            rev.append(max(-32767, min(32767, int(val))))
        arr = rev

    return arr


__all__ = ["biquad_resonance", "pitch_shift", "shift_pitch_and_formants"]
