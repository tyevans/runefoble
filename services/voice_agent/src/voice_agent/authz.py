"""Schema permission checks for voice_agent HTTP and WebSocket routes (TASK-0558).

Governed by:
- ADR-0001: SpiceDB Zanzibar object-level authorization. Every check names a
  permission from runefoble.zed through `ACTION_PERMISSIONS`.
- ADR-0015 (c): the subject is the verified principal, or the speaker that the
  request names when the principal holds `session.control`.

The SpiceDB client comes from the shared factory. SpiceDB failures are not denials:
they propagate, and the app maps them to 503 or 500 (`runefoble_auth.authz_http`).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException
from runefoble_auth.contract import permission_for_action
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.websocket import WebSocketAuthorizer

logger = logging.getLogger("runefoble.voice_agent.authz")


async def action_allowed(action: str, resource_id: str, subject_id: str) -> bool:
    """Return True when SpiceDB grants the action on the resource to the user subject."""
    resource_type, permission = permission_for_action(action)
    return await get_spicedb_client().check_permission(
        resource_type, resource_id, permission, "user", subject_id
    )


def _denial_detail(action: str, resource_id: str, subject_id: str) -> dict[str, Any]:
    resource_type, _ = permission_for_action(action)
    return {
        "error": "permission_denied",
        "required_permission": action,
        "resource": f"{resource_type}:{resource_id}",
        "subject": f"user:{subject_id}",
    }


async def require_action(action: str, resource_id: str, subject_id: str) -> None:
    """Raise HTTP 403 when the subject lacks the action on the resource."""
    if not await action_allowed(action, resource_id, subject_id):
        logger.warning("Voice permission denied: %s on %s for %s", action, resource_id, subject_id)
        raise HTTPException(status_code=403, detail=_denial_detail(action, resource_id, subject_id))


async def _speaker_failure(
    session_id: str, speaker_id: str, principal_id: str
) -> tuple[str, str] | None:
    """Return the (action, subject) that failed, or None when the speaker may participate."""
    if speaker_id != principal_id and not await action_allowed(
        "session.control", session_id, principal_id
    ):
        return "session.control", principal_id
    if not await action_allowed("session.participate", session_id, speaker_id):
        return "session.participate", speaker_id
    return None


async def speaker_allowed(session_id: str, speaker_id: str, principal_id: str) -> bool:
    """Return True when the named speaker may speak in the session as the principal."""
    return await _speaker_failure(session_id, speaker_id, principal_id) is None


async def require_speaker(session_id: str, speaker_id: str, principal_id: str) -> None:
    """Raise HTTP 403 unless the principal may act for the named speaker.

    The speaker must hold `session.participate`. A principal may act for another speaker
    only when the principal holds `session.control`.
    """
    failure = await _speaker_failure(session_id, speaker_id, principal_id)
    if failure is None:
        return
    action, subject = failure
    logger.warning("Voice speaker denied: %s on %s for %s", action, session_id, subject)
    raise HTTPException(status_code=403, detail=_denial_detail(action, session_id, subject))


def speaker_authorizer(session_id: str, speaker_id: str) -> WebSocketAuthorizer:
    """Build the socket check: the token subject may act as `speaker_id` in the session."""

    async def _check(principal_id: str) -> bool:
        return await speaker_allowed(session_id, speaker_id, principal_id)

    return _check


__all__ = [
    "action_allowed",
    "speaker_authorizer",
    "require_action",
    "require_speaker",
    "speaker_allowed",
]
