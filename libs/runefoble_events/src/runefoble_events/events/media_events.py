"""Voice audio, vocal DSP, soundscape, asset forge, and audience domain events."""

from runefoble_events.asset import (
    AssetDeleted,
    AssetGenerated,
    AssetUploaded,
    BattlemapCreated,
    BattlemapForged,
    TokenAssetForged,
)
from runefoble_events.audience import (
    AudienceModifierApproved,
    AudienceModifierProposed,
    AudiencePollCompleted,
    AudiencePollStarted,
    AudienceVoteCast,
)
from runefoble_events.soundscape import (
    ChannelVolumeChanged,
    DuckingEngaged,
    DuckingReleased,
    LeitmotifProfileConfigured,
    LeitmotifTriggered,
    MasterVolumeChanged,
    SoundscapeCueTriggered,
    SoundscapeTensionUpdated,
    SoundscapeTrackChanged,
    StemProfileOverridden,
)
from runefoble_events.vocal_dsp import (
    VocalModulatorPresetAppliedEvent,
    VoiceFilterToggledEvent,
)
from runefoble_events.voice import (
    MobileAudioProfileAdapted,
    MobileCompanionConnected,
    MobileHapticPingDispatched,
    VoicePeerJoined,
    VoicePeerLeft,
    VoicePeerMuteToggled,
    VoiceSpeechInterrupted,
    VoiceTranscriptionFailed,
)
from runefoble_events.voice_barge_in import (
    NeuralSpeechBargeInDetectedEvent,
    TTSStreamAttenuatedEvent,
)
from runefoble_events.voice_stream_quality import (
    VoiceStreamCodecAdaptedEvent,
    VoiceStreamQualityDegradedEvent,
)
from runefoble_events.watcher import (
    VoiceAudioConditioned,
)

__all__ = [
    "AssetDeleted",
    "AssetGenerated",
    "AssetUploaded",
    "AudienceModifierApproved",
    "AudienceModifierProposed",
    "AudiencePollCompleted",
    "AudiencePollStarted",
    "AudienceVoteCast",
    "BattlemapCreated",
    "BattlemapForged",
    "LeitmotifProfileConfigured",
    "LeitmotifTriggered",
    "MobileAudioProfileAdapted",
    "MobileCompanionConnected",
    "MobileHapticPingDispatched",
    "NeuralSpeechBargeInDetectedEvent",
    "ChannelVolumeChanged",
    "DuckingEngaged",
    "DuckingReleased",
    "MasterVolumeChanged",
    "SoundscapeCueTriggered",
    "SoundscapeTensionUpdated",
    "SoundscapeTrackChanged",
    "StemProfileOverridden",
    "TTSStreamAttenuatedEvent",
    "TokenAssetForged",
    "VocalModulatorPresetAppliedEvent",
    "VoiceAudioConditioned",
    "VoiceFilterToggledEvent",
    "VoicePeerJoined",
    "VoicePeerLeft",
    "VoicePeerMuteToggled",
    "VoiceSpeechInterrupted",
    "VoiceTranscriptionFailed",
    "VoiceStreamCodecAdaptedEvent",
    "VoiceStreamQualityDegradedEvent",
]
