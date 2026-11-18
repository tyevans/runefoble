"""Latest peer audio telemetry. Best effort, in process, and not durable (TASK-0577).

Telemetry is not domain state. It is never saved to the event store. Each replica keeps only the
latest sample per peer, in a bounded view. A restart clears the view. Each sample also feeds
OpenTelemetry instruments. With no meter provider configured, the instruments do nothing.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

from opentelemetry import metrics

MAX_SAMPLES = 10_000

_meter = metrics.get_meter("runefoble.voice_agent")
_updates = _meter.create_counter(
    "voice.telemetry.updates", unit="{update}", description="Peer audio telemetry updates"
)
_latency = _meter.create_histogram(
    "voice.telemetry.latency", unit="ms", description="Peer-reported audio latency"
)


@dataclass(frozen=True)
class PeerTelemetrySample:
    audio_level: float = 0.0
    latency_ms: float = 0.0
    is_speaking: bool = False


class PeerTelemetryView:
    """Latest sample per (session, peer). Least recently updated entries are dropped first."""

    def __init__(self, max_samples: int = MAX_SAMPLES) -> None:
        self._max = max_samples
        self._samples: OrderedDict[tuple[str, str], PeerTelemetrySample] = OrderedDict()

    def record(
        self,
        session_id: str,
        peer_id: str,
        *,
        audio_level: float | None,
        latency_ms: float | None,
        is_speaking: bool | None,
    ) -> PeerTelemetrySample:
        key = (session_id, peer_id)
        prev = self._samples.get(key, PeerTelemetrySample())
        sample = PeerTelemetrySample(
            audio_level=prev.audio_level if audio_level is None else audio_level,
            latency_ms=prev.latency_ms if latency_ms is None else latency_ms,
            is_speaking=prev.is_speaking if is_speaking is None else is_speaking,
        )
        self._samples[key] = sample
        self._samples.move_to_end(key)
        while len(self._samples) > self._max:
            self._samples.popitem(last=False)
        _updates.add(1)
        _latency.record(sample.latency_ms)
        return sample

    def for_session(self, session_id: str) -> dict[str, PeerTelemetrySample]:
        return {pid: s for (sid, pid), s in self._samples.items() if sid == session_id}

    def forget(self, session_id: str, peer_id: str) -> None:
        self._samples.pop((session_id, peer_id), None)


__all__ = ["MAX_SAMPLES", "PeerTelemetrySample", "PeerTelemetryView"]
