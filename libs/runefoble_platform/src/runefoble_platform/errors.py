"""Runefoble platform exceptions hierarchy."""

from typing import Any


class RunefobleError(Exception):
    """Base error for all Runefoble platform operations."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class EntityNotFoundError(RunefobleError):
    """Raised when a requested resource does not exist."""

    def __init__(self, entity_type: str, entity_id: str):
        super().__init__(
            f"{entity_type} with ID '{entity_id}' not found.",
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
            },
        )


class ConfigurationError(RunefobleError):
    """Raised when a required setting is missing or invalid. The process must not start."""


class ServiceUnavailableError(RunefobleError):
    """Raised when a service dependency is not ready. Maps to HTTP 503 (ADR-0015 b)."""
