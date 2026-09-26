"""Privacy-preserving sanitation and profile anonymization utilities."""

from __future__ import annotations

import hashlib
from typing import Any
from uuid import UUID

FORBIDDEN_PROPERTY_KEYS = {
    "transcript",
    "raw_transcript",
    "audio",
    "raw_audio",
    "speech",
    "dialogue",
    "password",
    "token",
    "secret",
    "email",
}


def anonymize_profile_id(
    profile_id: str | UUID | None, salt: str = "runefoble_privacy_salt"
) -> str | None:
    """Hash profile identifiers using salted SHA-256 to ensure player privacy."""
    if not profile_id:
        return None
    raw = str(profile_id).strip()
    if not raw:
        return None
    hasher = hashlib.sha256(f"{salt}:{raw}".encode())
    return hasher.hexdigest()[:32]


def sanitize_properties(properties: dict[str, Any] | None) -> dict[str, Any]:
    """Recursively scrub forbidden PII, audio bytes, and speech transcripts from properties."""
    if not properties:
        return {}
    sanitized: dict[str, Any] = {}
    for key, val in properties.items():
        lower_key = str(key).lower()
        if (
            lower_key in FORBIDDEN_PROPERTY_KEYS
            or "audio" in lower_key
            or "transcript" in lower_key
        ):
            continue
        if isinstance(val, dict):
            sanitized[key] = sanitize_properties(val)
        elif isinstance(val, (list, tuple)):
            sanitized[key] = [
                sanitize_properties(v) if isinstance(v, dict) else v
                for v in val
                if not (isinstance(v, str) and len(v) > 2048)
            ]
        elif isinstance(val, (UUID,)):
            sanitized[key] = str(val)
        else:
            sanitized[key] = val
    return sanitized


__all__ = [
    "FORBIDDEN_PROPERTY_KEYS",
    "anonymize_profile_id",
    "sanitize_properties",
]
