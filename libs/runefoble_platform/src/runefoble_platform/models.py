"""Shared time helper for platform and service models."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current time in UTC. The one wall-clock helper for Runefoble."""
    return datetime.now(UTC)
