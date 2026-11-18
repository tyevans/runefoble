"""The one UUID parsing policy for identifiers that arrive from clients (TASK-0816).

A typed identifier that is not a UUID is refused with HTTP 400. The error names the field.
The parser never substitutes a value: no random id and no derived id. A substitute would
write state under an id that the caller did not send.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException


class InvalidIdentifierError(HTTPException):
    """HTTP 400 for a malformed UUID. The detail names the field that was sent."""

    def __init__(self, field: str) -> None:
        super().__init__(status_code=400, detail=f"Invalid UUID for field '{field}'")


def parse_uuid(value: UUID | str | None, *, field: str) -> UUID:
    """Return the UUID for `value`, or raise InvalidIdentifierError naming `field`."""
    if isinstance(value, UUID):
        return value
    try:
        return UUID(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise InvalidIdentifierError(field) from exc


def parse_optional_uuid(value: UUID | str | None, *, field: str) -> UUID | None:
    """Return None for an absent or empty value. Otherwise apply `parse_uuid`."""
    if value is None or value == "":
        return None
    return parse_uuid(value, field=field)
