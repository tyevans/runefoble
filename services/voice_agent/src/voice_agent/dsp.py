"""Digital Signal Processing (DSP) Audio Conditioning and Slur Engine.

Provides real-time speech transformation, phonetic slurs, audio filter coefficient
computation, and fast digital signal processing filter chains for tabletop afflictions.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from voice_agent.audio_utils import (
    _to_samples_array,
    generate_synthetic_audio,
    to_samples_array,
)
from voice_agent.filters import (
    apply_audio_filters,
    drunk_filter,
    ethereal_filter,
    underwater_filter,
    whisper_filter,
)
from voice_agent.phonetics import (
    apply_slurred_speech,
    apply_text_transforms,
    slur_phonemes,
)


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


class VoiceDSPPipeline:
    """Pipeline for transforming speech text and computing DSP filter parameters."""

    def slur_phonemes(self, text: str) -> str:
        """Inject inebriated slurs, elongated vowels, and hiccups into text."""
        return slur_phonemes(text)

    def apply_text_transforms(self, text: str, filters: list[str]) -> str:
        """Apply text conditioning according to active affliction filters."""
        return apply_text_transforms(text, filters)

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


__all__ = [
    "DSPFilterConfig",
    "ProcessedSpeechResult",
    "VoiceDSPPipeline",
    "_to_samples_array",
    "apply_audio_filters",
    "apply_slurred_speech",
    "apply_text_transforms",
    "drunk_filter",
    "ethereal_filter",
    "generate_synthetic_audio",
    "slur_phonemes",
    "to_samples_array",
    "underwater_filter",
    "whisper_filter",
]
