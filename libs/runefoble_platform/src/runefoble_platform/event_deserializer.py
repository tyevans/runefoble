"""Payload deserialization and event registry resolution for Redis Streams."""

from __future__ import annotations

import logging
from typing import Any

from eventsource.adapters.serialization.json import json_loads
from eventsource.domain.event_registry import get_event_class_or_none

logger = logging.getLogger(__name__)


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


def deserialize_event(fields: dict[str, Any] | str) -> Any:
    """Deserialize Redis stream fields into a registered DomainEvent or dictionary."""
    if isinstance(fields, str):
        try:
            fields = json_loads(fields)
        except Exception:
            return fields

    if not isinstance(fields, dict):
        return fields

    event_dict: Any = fields
    event_type: str | None = fields.get("event_type")

    if "payload" in fields:
        raw_payload = fields["payload"]
        if isinstance(raw_payload, str):
            try:
                parsed = json_loads(raw_payload)
                event_dict = parsed if isinstance(parsed, dict) else {"data": parsed}
            except Exception:
                event_dict = {"raw": raw_payload}
        elif isinstance(raw_payload, dict):
            event_dict = raw_payload

    if isinstance(event_dict, dict):
        _inject_trace_meta(event_dict, fields)
        if not event_type:
            event_type = event_dict.get("event_type") or event_dict.get("type")

    if event_type and isinstance(event_dict, dict):
        event_cls = get_event_class_or_none(str(event_type))
        if event_cls is None and "." in str(event_type):
            event_cls = get_event_class_or_none(str(event_type).split(".")[-1])

        if event_cls is not None:
            try:
                event_obj = event_cls.model_validate(event_dict)
                _inject_trace_meta(event_obj, fields)
                return event_obj
            except Exception as e:
                logger.warning("Event validation failed for '%s': %s", event_type, e)
        else:
            _inject_trace_meta(event_dict, fields)

    return event_dict


__all__ = ["deserialize_event"]
