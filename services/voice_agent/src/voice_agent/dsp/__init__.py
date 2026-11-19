"""DSP Audio Processing, Formant Scaling, and NPC Vocal Presets."""

from __future__ import annotations

from voice_agent.dsp.barge_in_filter import BargeInOnsetFilter, BargeInOnsetResult
from voice_agent.dsp.base import (
    DSPFilterConfig,
    ProcessedSpeechResult,
    VoiceDSPPipeline,
)
from voice_agent.dsp.cosine_crossfade import (
    CosineAttenuationResult,
    CosineCrossfadeAttenuator,
    apply_cosine_crossfade,
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

__all__ = [
    "ANCIENT_DRAGON",
    "BargeInOnsetFilter",
    "BargeInOnsetResult",
    "CELESTIAL_SPIRIT",
    "CosineAttenuationResult",
    "CosineCrossfadeAttenuator",
    "DSPFilterConfig",
    "GOBLIN_SKULKER",
    "NPCVoicePreset",
    "PRESETS_BY_ID",
    "PRESETS_BY_NAME",
    "ProcessedSpeechResult",
    "ROBOTIC_CONSTRUCT",
    "StreamPipelineFilter",
    "VoiceDSPPipeline",
    "apply_cosine_crossfade",
    "biquad_resonance",
    "get_preset",
    "list_presets",
    "pitch_shift",
    "shift_pitch_and_formants",
]
