"""Vocal Modulator and Real-Time NPC Formant DSP Domain Events."""

from __future__ import annotations

import time
from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("voice.modulator_preset_applied")
@register_event("runefoble.events.voice.modulator_preset_applied")
class VocalModulatorPresetAppliedEvent(BaseRunefobleEvent):
    """Emitted when a DM vocal modulator preset is applied to an outgoing audio stream."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "VoiceRoom"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.voice.modulator_preset_applied"
    session_id: str
    peer_id: str
    preset_name: str
    pitch_shift_semitones: float = 0.0
    formant_shift: float = 1.0
    resonance_hz: float = 0.0
    octave_offset: float = 0.0
    reverb_wet: float = 0.0
    active_filters: list[str] = Field(default_factory=list)
    user_id: str = ""
    applied_at: float = Field(default_factory=time.time)


@register_event("voice.filter_toggled")
@register_event("runefoble.events.voice.filter_toggled")
class VoiceFilterToggledEvent(BaseRunefobleEvent):
    """Emitted when a live voice filter parameter or node is toggled on/off."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "VoiceRoom"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.voice.filter_toggled"
    session_id: str
    peer_id: str
    filter_name: str
    enabled: bool = True
    parameters: dict[str, float] = Field(default_factory=dict)
    user_id: str = ""
    toggled_at: float = Field(default_factory=time.time)


# Backward-compatible aliases
VocalModulatorPresetApplied = VocalModulatorPresetAppliedEvent
VoiceFilterToggled = VoiceFilterToggledEvent

__all__ = [
    "VocalModulatorPresetApplied",
    "VocalModulatorPresetAppliedEvent",
    "VoiceFilterToggled",
    "VoiceFilterToggledEvent",
]
