"""Wall clock for campaign invite expiry.

Tests replace `utc_now` on this module to move time forward. Callers must read it
through the module attribute, not through a copied reference.
"""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current time in UTC."""
    return datetime.now(UTC)
