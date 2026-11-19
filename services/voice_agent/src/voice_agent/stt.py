"""Streaming Speech-To-Text (STT) and Voice Activity Detection (VAD) Pipeline.

Provides ring buffering per participant, sub-250ms silence VAD segmentation,
and Whisper acoustic inference integration for sub-500ms tabletop voice actions.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from runefoble_events.events import PlayerSpokeEvent
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_publish import publish_or_fail
from runefoble_platform.identifiers import opaque_aggregate_id
from voice_agent.event_bus import get_event_bus
from voice_agent.speech_settings import VoiceAgentSettings, build_transcriber
from voice_agent.transcriber import BaseTranscriber
from voice_agent.vad import (
    AudioRingBuffer,
    VADSegmenter,
    parse_audio_data,
)
from voice_agent.watcher_intent import (
    IntentForwardResult,
    WatcherIntentPort,
    build_watcher_intent_port,
)

logger = logging.getLogger("runefoble.voice_agent.stt")
STREAM_SESSION = "runefoble.events.session"
STREAM_VOICE = "runefoble.events.voice"

__all__ = [
    "AudioRingBuffer",
    "BaseTranscriber",
    "ChunkProcessingResult",
    "ParticipantAudioState",
    "StreamingAudioPipeline",
    "VADSegmenter",
    "get_streaming_pipeline",
    "parse_audio_data",
    "set_streaming_pipeline",
]


class ChunkProcessingResult(BaseModel):
    """Result of ingesting and evaluating an audio frame chunk."""

    session_id: str
    speaker_id: str
    speaker_name: str
    speech_detected: bool = False
    utterance_complete: bool = False
    transcript: str | None = None
    latency_ms: float = 0.0
    event_id: str | None = None
    watcher_intent: dict[str, Any] | None = None
    # Why The Watcher did not take the transcript. None when it answered (TASK-0732).
    watcher_error: str | None = None
    vad_state: str = "silence"
    buffer_duration_ms: float = 0.0


class ParticipantAudioState:
    def __init__(
        self,
        sample_rate: int = 16000,
        silence_threshold_ms: float = 200.0,
        energy_threshold: float = 350.0,
    ):
        self.ring_buffer = AudioRingBuffer()
        self.vad = VADSegmenter(
            sample_rate=sample_rate,
            silence_threshold_ms=silence_threshold_ms,
            energy_threshold=energy_threshold,
        )
        self.last_activity: float = time.time()


@dataclass(frozen=True)
class _Segment:
    """What buffering and VAD found in one chunk."""

    speech_detected: bool
    utterance_audio: bytes | None
    sample_rate: int
    vad_state: str
    buffer_duration_ms: float


class StreamingAudioPipeline:
    """Manages audio ring buffers, VAD boundaries, Whisper transcription, and event dispatch."""

    def __init__(
        self,
        transcriber: BaseTranscriber,
        watcher: WatcherIntentPort,
        silence_threshold_ms: float = 200.0,
        energy_threshold: float = 350.0,
    ):
        self.transcriber: BaseTranscriber = transcriber
        self.watcher: WatcherIntentPort = watcher
        self.silence_threshold_ms = silence_threshold_ms
        self.energy_threshold = energy_threshold
        self.participants: dict[str, ParticipantAudioState] = {}

    def get_or_create_participant(
        self, session_id: str, speaker_id: str, sample_rate: int = 16000
    ) -> ParticipantAudioState:
        key = f"{session_id}:{speaker_id}"
        if key not in self.participants:
            self.participants[key] = ParticipantAudioState(
                sample_rate=sample_rate,
                silence_threshold_ms=self.silence_threshold_ms,
                energy_threshold=self.energy_threshold,
            )
        state = self.participants[key]
        state.last_activity = time.time()
        return state

    def reset_participant(self, session_id: str, speaker_id: str) -> None:
        key = f"{session_id}:{speaker_id}"
        if key in self.participants:
            self.participants[key].ring_buffer.clear()
            self.participants[key].vad.reset_utterance()
            del self.participants[key]

    def reset_all(self) -> None:
        self.participants.clear()

    def _segment(
        self, session_id: str, speaker_id: str, audio_bytes: bytes, sample_rate: int, is_final: bool
    ) -> _Segment:
        """Buffer the chunk and run VAD. Return the finished utterance audio, if any."""
        participant = self.get_or_create_participant(session_id, speaker_id, sample_rate)
        pcm_bytes, sr = parse_audio_data(audio_bytes, default_sample_rate=sample_rate)
        if pcm_bytes:
            participant.ring_buffer.write(pcm_bytes)
        speech_detected, utterance_complete, utterance_audio = participant.vad.process_audio_chunk(
            pcm_bytes, is_final=is_final
        )
        if utterance_complete:
            vad_state = "utterance_complete"
        elif speech_detected:
            vad_state = "speech_active"
        else:
            vad_state = "silence"
        return _Segment(
            speech_detected=speech_detected,
            utterance_audio=utterance_audio if utterance_complete and utterance_audio else None,
            sample_rate=sr,
            vad_state=vad_state,
            buffer_duration_ms=participant.ring_buffer.duration_ms(sr),
        )

    async def _forward_transcript(
        self, payload: dict[str, Any], caller_authorization: str | None
    ) -> IntentForwardResult:
        """Send the transcript to The Watcher with the speaker's own bearer (ADR-0015 c)."""
        forwarded = await self.watcher.forward(payload, caller_authorization)
        if forwarded.error is not None:
            logger.warning("The Watcher did not take the streaming transcript: %s", forwarded.error)
        return forwarded

    async def process_chunk(
        self,
        session_id: str,
        speaker_id: str,
        speaker_name: str,
        campaign_id: str | None = None,
        audio_bytes: bytes = b"",
        sample_rate: int = 16000,
        is_whisper: bool = False,
        target_character_id: str | None = None,
        is_final: bool = False,
        caller_authorization: str | None = None,
    ) -> ChunkProcessingResult:
        """Buffer, segment, transcribe, publish, and forward one chunk.

        A failed publish raises DomainEventPublishError (ADR-0015 f). A failed Watcher call
        does not fail the chunk. The result keeps the transcript and sets `watcher_error`.
        """
        start_t = time.perf_counter()
        segment = self._segment(session_id, speaker_id, audio_bytes, sample_rate, is_final)
        result = ChunkProcessingResult(
            session_id=session_id,
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            speech_detected=segment.speech_detected,
            vad_state=segment.vad_state,
            buffer_duration_ms=segment.buffer_duration_ms,
        )
        if segment.utterance_audio is None:
            result.latency_ms = _elapsed_ms(start_t)
            return result

        transcript = await self.transcriber.transcribe(
            segment.utterance_audio, sample_rate=segment.sample_rate
        )
        event_id = await _publish_spoken(
            session_id=session_id,
            campaign_id=campaign_id,
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            transcript=transcript,
            is_whisper=is_whisper,
            target_character_id=target_character_id,
        )
        forwarded = await self._forward_transcript(
            {
                "speaker_id": speaker_id,
                "speaker_name": speaker_name,
                "transcript": transcript,
                "session_id": session_id,
                "campaign_id": campaign_id or session_id,
            },
            caller_authorization,
        )
        result.speech_detected = True
        result.utterance_complete = True
        result.transcript = transcript
        result.event_id = event_id
        result.watcher_intent = forwarded.intent
        result.watcher_error = forwarded.error
        result.latency_ms = _elapsed_ms(start_t)
        return result


def _elapsed_ms(start_t: float) -> float:
    return round((time.perf_counter() - start_t) * 1000.0, 2)


async def _publish_spoken(
    *,
    session_id: str,
    campaign_id: str | None,
    speaker_id: str,
    speaker_name: str,
    transcript: str,
    is_whisper: bool,
    target_character_id: str | None,
) -> str:
    """Publish the PlayerSpokeEvent. The spoken words are player state (ADR-0015 f)."""
    session_uuid = opaque_aggregate_id(session_id, field="session_id")
    campaign_uuid = opaque_aggregate_id(campaign_id, field="campaign_id") if campaign_id else None
    event = PlayerSpokeEvent(
        aggregate_id=session_uuid,
        session_id=session_uuid,
        campaign_id=campaign_uuid,
        speaker_id=speaker_id,
        speaker_name=speaker_name,
        transcript=transcript,
        is_whisper=is_whisper,
        target_character_id=target_character_id,
    )
    return await publish_or_fail(get_event_bus(), STREAM_SESSION, event)


_pipeline: StreamingAudioPipeline | None = None


def get_streaming_pipeline() -> StreamingAudioPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = StreamingAudioPipeline(
            transcriber=build_transcriber(VoiceAgentSettings()),
            watcher=build_watcher_intent_port(PlatformSettings()),
        )
    return _pipeline


def set_streaming_pipeline(pipeline: StreamingAudioPipeline | None) -> None:
    global _pipeline
    _pipeline = pipeline
