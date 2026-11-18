"""The one identifier policy for ids that arrive from clients (TASK-0816).

Two kinds of id exist. Use the kind that the domain defines:

- Strict UUID (`parse_uuid`, `parse_optional_uuid`): the domain creates the id as a UUID
  (campaigns, settlements, bounties, shared worlds). A malformed value is HTTP 400 and
  names the field.
- Opaque id (`opaque_aggregate_id`): the domain treats the id as a string key (session
  ids, game ids, faction ids). Its stream id is a deterministic UUIDv5 of the string, so
  every call maps the same key to the same stream.

No function in this module draws a random id. A missing or malformed value is an error.
"""

from __future__ import annotations

from uuid import NAMESPACE_DNS, UUID, uuid5

from fastapi import HTTPException


class InvalidIdentifierError(HTTPException):
    """HTTP 400 for a missing or malformed id. The detail names the field."""

    def __init__(self, field: str) -> None:
        super().__init__(status_code=400, detail=f"Invalid id for field '{field}'")


def parse_uuid(value: UUID | str | None, *, field: str) -> UUID:
    """Return the UUID for `value`. A missing or malformed value raises InvalidIdentifierError."""
    if isinstance(value, UUID):
        return value
    if value is None or value == "":
        raise InvalidIdentifierError(field)
    try:
        return UUID(str(value))
    except ValueError as exc:
        raise InvalidIdentifierError(field) from exc


def parse_optional_uuid(value: UUID | str | None, *, field: str) -> UUID | None:
    """Return None only for an absent optional field. Otherwise apply `parse_uuid`."""
    if value is None or value == "":
        return None
    return parse_uuid(value, field=field)


def opaque_aggregate_id(value: UUID | str | None, *, field: str) -> UUID:
    """Return the stream id for an opaque key.

    A UUID value is returned as is. Any other non-empty string maps to
    `uuid5(NAMESPACE_DNS, value)`. The mapping is stable across calls and processes.
    """
    if isinstance(value, UUID):
        return value
    if value is None or value == "":
        raise InvalidIdentifierError(field)
    text = str(value)
    try:
        return UUID(text)
    except ValueError:
        return uuid5(NAMESPACE_DNS, text)


def opaque_optional_aggregate_id(value: UUID | str | None, *, field: str) -> UUID | None:
    """Return None for an absent optional key. Otherwise apply `opaque_aggregate_id`."""
    if value is None or value == "":
        return None
    return opaque_aggregate_id(value, field=field)
