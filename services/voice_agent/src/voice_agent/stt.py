"""Streaming Speech-To-Text (STT) and Voice Activity Detection (VAD) Pipeline.

Provides ring buffering per participant, sub-250ms silence VAD segmentation,
and Whisper acoustic inference integration for sub-500ms tabletop voice actions.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

import httpx
from pydantic import BaseModel
from runefoble_events.events import PlayerSpokeEvent, VoiceTranscriptionFailed
from runefoble_platform.engine_ports import EngineUnavailableError
from runefoble_platform.event_publish import publish_best_effort, publish_or_fail
from voice_agent.auth import caller_headers
from voice_agent.event_bus import get_event_bus
from voice_agent.speech_settings import VoiceAgentSettings, build_transcriber
from voice_agent.transcriber import BaseTranscriber
from voice_agent.vad import (
    AudioRingBuffer,
    VADSegmenter,
    parse_audio_data,
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


def to_uuid(val: str | UUID | None) -> UUID:
    """Deterministically convert string or UUID into a valid UUID."""
    if val is None:
        return uuid4()
    if isinstance(val, UUID):
        return val
    try:
        return UUID(val)
    except ValueError:
        return uuid5(NAMESPACE_DNS, str(val))


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


class StreamingAudioPipeline:
    """Manages audio ring buffers, VAD boundaries, Whisper transcription, and event dispatch."""

    def __init__(
        self,
        transcriber: BaseTranscriber,
        silence_threshold_ms: float = 200.0,
        energy_threshold: float = 350.0,
    ):
        self.transcriber: BaseTranscriber = transcriber
        self.silence_threshold_ms = silence_threshold_ms
        self.energy_threshold = energy_threshold
        self.participants: dict[str, ParticipantAudioState] = {}
        self._watcher_client: httpx.AsyncClient | None = None
        self._watcher_url: str = os.environ.get("RUNEFOBLE_WATCHER_URL", "http://the-watcher:8001")

    def set_watcher_client(self, client: httpx.AsyncClient | None) -> None:
        self._watcher_client = client

    def set_watcher_url(self, url: str) -> None:
        self._watcher_url = url

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

    async def publish_transcription_failed(
        self,
        session_id: str,
        speaker_id: str,
        speaker_name: str,
        exc: EngineUnavailableError,
    ) -> None:
        event = VoiceTranscriptionFailed(
            session_id=session_id,
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            engine=self.transcriber.engine_name,
            reason=str(exc),
        )
        await publish_best_effort(get_event_bus(), STREAM_VOICE, event)

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
        start_t = time.perf_counter()
        participant = self.get_or_create_participant(session_id, speaker_id, sample_rate)

        pcm_bytes, sr = parse_audio_data(audio_bytes, default_sample_rate=sample_rate)

        if pcm_bytes:
            participant.ring_buffer.write(pcm_bytes)

        speech_detected, utterance_complete, utterance_audio = participant.vad.process_audio_chunk(
            pcm_bytes, is_final=is_final
        )

        vad_state = "silence"
        if utterance_complete:
            vad_state = "utterance_complete"
        elif speech_detected:
            vad_state = "speech_active"

        buf_dur = participant.ring_buffer.duration_ms(sr)

        if not utterance_complete or not utterance_audio:
            elapsed_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
            return ChunkProcessingResult(
                session_id=session_id,
                speaker_id=speaker_id,
                speaker_name=speaker_name,
                speech_detected=speech_detected,
                utterance_complete=False,
                transcript=None,
                latency_ms=elapsed_ms,
                vad_state=vad_state,
                buffer_duration_ms=buf_dur,
            )

        try:
            transcript = await self.transcriber.transcribe(utterance_audio, sample_rate=sr)
        except EngineUnavailableError as exc:
            await self.publish_transcription_failed(session_id, speaker_id, speaker_name, exc)
            raise

        session_uuid = to_uuid(session_id)
        campaign_uuid = to_uuid(campaign_id) if campaign_id else None
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

        # The spoken words are player state. A failed publish fails the chunk (ADR-0015 f).
        event_id = await publish_or_fail(get_event_bus(), STREAM_SESSION, event)

        watcher_intent = None
        try:
            watcher_payload = {
                "speaker_id": speaker_id,
                "speaker_name": speaker_name,
                "transcript": transcript,
                "session_id": session_id,
                "campaign_id": campaign_id or session_id,
            }
            # The Watcher takes identity only from a verified bearer. The speaker's own token
            # is forwarded on their behalf (ADR-0015 c).
            watcher_headers = caller_headers(caller_authorization)
            if self._watcher_client:
                resp = await self._watcher_client.post(
                    "/api/v1/watcher/transcribe-and-act",
                    json=watcher_payload,
                    headers=watcher_headers,
                )
                if resp.status_code == 200:
                    watcher_intent = resp.json()
            else:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(
                        f"{self._watcher_url}/api/v1/watcher/transcribe-and-act",
                        json=watcher_payload,
                        headers=watcher_headers,
                    )
                    if resp.status_code == 200:
                        watcher_intent = resp.json()
        except Exception as e:
            logger.warning("Failed to forward streaming transcript to The Watcher: %s", e)

        latency_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
        return ChunkProcessingResult(
            session_id=session_id,
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            speech_detected=True,
            utterance_complete=True,
            transcript=transcript,
            latency_ms=latency_ms,
            event_id=event_id,
            watcher_intent=watcher_intent,
            vad_state=vad_state,
            buffer_duration_ms=buf_dur,
        )


_pipeline: StreamingAudioPipeline | None = None


def get_streaming_pipeline() -> StreamingAudioPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = StreamingAudioPipeline(transcriber=build_transcriber(VoiceAgentSettings()))
    return _pipeline


def set_streaming_pipeline(pipeline: StreamingAudioPipeline | None) -> None:
    global _pipeline
    _pipeline = pipeline
