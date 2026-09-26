"""Voice Activity Detection (VAD) and Audio Ring Buffer for Streaming STT."""

from __future__ import annotations

import array
import math
import struct
from collections import deque


def parse_audio_data(data_bytes: bytes, default_sample_rate: int = 16000) -> tuple[bytes, int]:
    """Extract raw PCM bytes and sample rate from PCM or WAV audio bytes."""
    if not data_bytes:
        return b"", default_sample_rate
    if data_bytes.startswith(b"RIFF") and len(data_bytes) >= 44:
        try:
            sr = struct.unpack("<I", data_bytes[24:28])[0]
            pos = 12
            while pos < len(data_bytes) - 8:
                chunk_id = data_bytes[pos : pos + 4]
                chunk_size = struct.unpack("<I", data_bytes[pos + 4 : pos + 8])[0]
                if chunk_id == b"data":
                    pcm_bytes = data_bytes[pos + 8 : pos + 8 + chunk_size]
                    return pcm_bytes, sr
                pos += 8 + chunk_size
            return data_bytes[44:], sr
        except Exception:
            return data_bytes[44:], default_sample_rate
    return data_bytes, default_sample_rate


class AudioRingBuffer:
    """Circular ring buffer for participant live PCM audio frames."""

    def __init__(self, capacity_bytes: int = 960000):  # ~30s of 16kHz 16-bit mono
        self.capacity_bytes = capacity_bytes
        self._buffer = bytearray()

    def write(self, data: bytes) -> None:
        if not data:
            return
        overflow = (len(self._buffer) + len(data)) - self.capacity_bytes
        if overflow > 0:
            if overflow >= len(self._buffer):
                self._buffer.clear()
            else:
                del self._buffer[:overflow]
        self._buffer.extend(data)

    def read(self, num_bytes: int | None = None) -> bytes:
        if num_bytes is None or num_bytes >= len(self._buffer):
            return bytes(self._buffer)
        return bytes(self._buffer[-num_bytes:])

    def clear(self) -> None:
        self._buffer.clear()

    def duration_ms(self, sample_rate: int = 16000) -> float:
        bytes_per_sample = 2
        return (len(self._buffer) / (sample_rate * bytes_per_sample)) * 1000.0

    def __len__(self) -> int:
        return len(self._buffer)


class VADSegmenter:
    """Voice Activity Detection segmenter detecting speech and silence boundaries."""

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: float = 20.0,
        energy_threshold: float = 350.0,
        silence_threshold_ms: float = 200.0,
        min_speech_duration_ms: float = 60.0,
        max_utterance_duration_ms: float = 15000.0,
        pre_speech_padding_ms: float = 100.0,
    ):
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.energy_threshold = energy_threshold
        self.silence_threshold_ms = silence_threshold_ms
        self.min_speech_duration_ms = min_speech_duration_ms
        self.max_utterance_duration_ms = max_utterance_duration_ms

        self.bytes_per_sample = 2
        self.samples_per_frame = int(sample_rate * (frame_duration_ms / 1000.0))
        self.frame_bytes_size = self.samples_per_frame * self.bytes_per_sample

        pre_frames_count = max(1, int(pre_speech_padding_ms / frame_duration_ms))
        self._pre_speech_buffer: deque[bytes] = deque(maxlen=pre_frames_count)

        self.is_speech_active = False
        self.silence_duration_ms = 0.0
        self.speech_duration_ms = 0.0
        self._current_utterance = bytearray()
        self._residual_bytes = bytearray()

    def reset_utterance(self) -> None:
        self.is_speech_active = False
        self.silence_duration_ms = 0.0
        self.speech_duration_ms = 0.0
        self._current_utterance.clear()
        self._residual_bytes.clear()
        self._pre_speech_buffer.clear()

    def calculate_rms(self, frame_bytes: bytes) -> float:
        if not frame_bytes:
            return 0.0
        samples = array.array("h", frame_bytes)
        if not samples:
            return 0.0
        sum_sq = sum(s * s for s in samples)
        return math.sqrt(sum_sq / len(samples))

    def process_audio_chunk(
        self, chunk_bytes: bytes, is_final: bool = False
    ) -> tuple[bool, bool, bytes | None]:
        """Process incoming PCM audio chunk through sub-250ms VAD segmentation.

        Returns: (speech_detected, utterance_complete, utterance_audio)
        """
        if chunk_bytes:
            self._residual_bytes.extend(chunk_bytes)

        completed_utterance: bytes | None = None
        has_speech_in_chunk = False

        while len(self._residual_bytes) >= self.frame_bytes_size:
            frame = bytes(self._residual_bytes[: self.frame_bytes_size])
            del self._residual_bytes[: self.frame_bytes_size]

            rms = self.calculate_rms(frame)
            is_frame_speech = rms >= self.energy_threshold

            if is_frame_speech:
                has_speech_in_chunk = True
                if not self.is_speech_active:
                    self.is_speech_active = True
                    self.speech_duration_ms = 0.0
                    self.silence_duration_ms = 0.0
                    for pre_frame in self._pre_speech_buffer:
                        self._current_utterance.extend(pre_frame)
                    self._pre_speech_buffer.clear()

                self.speech_duration_ms += self.frame_duration_ms
                self.silence_duration_ms = 0.0
                self._current_utterance.extend(frame)
            else:
                if self.is_speech_active:
                    self.silence_duration_ms += self.frame_duration_ms
                    self._current_utterance.extend(frame)

                    if self.silence_duration_ms >= self.silence_threshold_ms:
                        if self.speech_duration_ms >= self.min_speech_duration_ms:
                            completed_utterance = bytes(self._current_utterance)
                            self.reset_utterance()
                            return True, True, completed_utterance
                        else:
                            self.reset_utterance()
                else:
                    self._pre_speech_buffer.append(frame)

        if is_final:
            if self.is_speech_active and self.speech_duration_ms >= self.min_speech_duration_ms:
                completed_utterance = bytes(self._current_utterance)
                self.reset_utterance()
                return True, True, completed_utterance
            else:
                self.reset_utterance()
                return False, False, None

        if self.speech_duration_ms >= self.max_utterance_duration_ms:
            completed_utterance = bytes(self._current_utterance)
            self.reset_utterance()
            return True, True, completed_utterance

        return (self.is_speech_active or has_speech_in_chunk), False, None
