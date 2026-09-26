"""Backward-compatibility alias for runefoble_platform.analytics.privacy."""

from __future__ import annotations

from runefoble_platform.analytics.privacy import (
    FORBIDDEN_PROPERTY_KEYS,
    anonymize_profile_id,
    sanitize_properties,
)

__all__ = [
    "FORBIDDEN_PROPERTY_KEYS",
    "anonymize_profile_id",
    "sanitize_properties",
]
