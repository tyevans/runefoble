"""DSP Audio Processing, Formant Scaling, and NPC Vocal Presets."""

from __future__ import annotations

from voice_agent.audio_utils import (
    _to_samples_array,
    generate_synthetic_audio,
    to_samples_array,
)
from voice_agent.dsp.base import (
    DSPFilterConfig,
    ProcessedSpeechResult,
    VoiceDSPPipeline,
)
from voice_agent.dsp.formants import (
    biquad_resonance,
    pitch_shift,
    shift_pitch_and_formants,
)
from voice_agent.dsp.pipeline import StreamPipelineFilter
from voice_agent.dsp.presets import (
    ANCIENT_DRAGON,
    CELESTIAL_SPIRIT,
    GOBLIN_SKULKER,
    PRESETS_BY_ID,
    PRESETS_BY_NAME,
    ROBOTIC_CONSTRUCT,
    NPCVoicePreset,
    get_preset,
    list_presets,
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

__all__ = [
    "ANCIENT_DRAGON",
    "CELESTIAL_SPIRIT",
    "DSPFilterConfig",
    "GOBLIN_SKULKER",
    "NPCVoicePreset",
    "PRESETS_BY_ID",
    "PRESETS_BY_NAME",
    "ProcessedSpeechResult",
    "ROBOTIC_CONSTRUCT",
    "StreamPipelineFilter",
    "VoiceDSPPipeline",
    "_to_samples_array",
    "apply_audio_filters",
    "apply_slurred_speech",
    "apply_text_transforms",
    "biquad_resonance",
    "drunk_filter",
    "ethereal_filter",
    "generate_synthetic_audio",
    "get_preset",
    "list_presets",
    "pitch_shift",
    "shift_pitch_and_formants",
    "slur_phonemes",
    "to_samples_array",
    "underwater_filter",
    "whisper_filter",
]
