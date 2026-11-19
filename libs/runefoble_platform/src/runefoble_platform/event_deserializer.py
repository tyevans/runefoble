"""Payload deserialization and event registry resolution for Redis Streams.

`deserialize_event` returns one of two kinds of value:

- A registered `DomainEvent` subclass, validated against its model.
- An `UnknownEvent` for an event type that has no registered class.

Any other input raises `EventDecodeError`. The function never returns raw input.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from eventsource.adapters.serialization.json import json_loads
from eventsource.domain.event_registry import get_event_class_or_none
from pydantic import ValidationError

from runefoble_platform.errors import RunefobleError

logger = logging.getLogger(__name__)


class EventDecodeError(RunefobleError):
    """A stream message cannot be decoded into an event. The message text gives the reason."""


@dataclass(frozen=True)
class UnknownEvent:
    """A decoded stream message whose event type has no registered class.

    `fields` holds the decoded payload object, with trace context copied in when present.
    """

    event_type: str
    fields: dict[str, Any] = field(default_factory=dict)


def _inject_trace_meta(target: Any, fields: dict[str, Any]) -> None:
    meta = target.get("metadata") if isinstance(target, dict) else getattr(target, "metadata", None)
    if isinstance(meta, dict):
        for key in ("traceparent", "tracestate"):
            if key in fields and key not in meta:
                meta[key] = fields[key]
    elif isinstance(target, dict):
        for key in ("traceparent", "tracestate"):
            if key in fields and key not in target:
                target[key] = fields[key]


def _parse_json_object(raw: str, what: str) -> dict[str, Any]:
    try:
        parsed = json_loads(raw)
    except ValueError as exc:
        raise EventDecodeError(f"{what} is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise EventDecodeError(f"{what} is not a JSON object")
    return parsed


def _payload_of(envelope: dict[str, Any]) -> dict[str, Any]:
    if "payload" not in envelope:
        return envelope
    raw_payload = envelope["payload"]
    if isinstance(raw_payload, str):
        return _parse_json_object(raw_payload, "payload")
    if isinstance(raw_payload, dict):
        return raw_payload
    raise EventDecodeError(
        f"payload must be a JSON string or a mapping, not {type(raw_payload).__name__}"
    )


def _event_type_of(envelope: dict[str, Any], event_dict: dict[str, Any]) -> str:
    raw_type = envelope.get("event_type") or event_dict.get("event_type") or event_dict.get("type")
    if not raw_type:
        raise EventDecodeError("stream fields carry no event_type")
    return str(raw_type)


def deserialize_event(fields: dict[str, Any] | str) -> Any:
    """Deserialize Redis stream fields into a registered DomainEvent or an UnknownEvent.

    Raise EventDecodeError when the input is not a JSON object, the payload is not a JSON
    object, the event type is missing, or a registered event fails validation.
    """
    envelope = _parse_json_object(fields, "stream fields") if isinstance(fields, str) else fields
    if not isinstance(envelope, dict):
        raise EventDecodeError(f"stream fields must be a mapping, not {type(envelope).__name__}")

    event_dict = _payload_of(envelope)
    _inject_trace_meta(event_dict, envelope)
    event_type = _event_type_of(envelope, event_dict)

    event_cls = get_event_class_or_none(event_type)
    if event_cls is None:
        return UnknownEvent(event_type=event_type, fields=event_dict)

    try:
        event_obj = event_cls.model_validate(event_dict)
    except ValidationError as exc:
        raise EventDecodeError(f"'{event_type}' failed validation: {exc}") from exc
    _inject_trace_meta(event_obj, envelope)
    return event_obj


__all__ = ["EventDecodeError", "UnknownEvent", "deserialize_event"]
