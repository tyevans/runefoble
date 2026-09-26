"""Digital Signal Processing (DSP) Audio Conditioning and Slur Engine.

Provides real-time speech transformation, phonetic slurs, and audio
filter coefficient computation for tabletop afflictions and DM penalties.
"""

import re

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

        if "ghostly" in filters_clean:
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

        if "ghostly" in filters_clean:
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
