"""SpiceDB tuple writes for campaign ownership, membership, and session links.

Callers write a tuple only after the matching aggregate save has succeeded (ADR-0001).
A failed write surfaces as 503. It is never logged and ignored.
Relations come from libs/runefoble_auth/schema/runefoble.zed. No role name grants access here.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from game_session.campaign.errors import AuthorizationStoreError
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient

logger = logging.getLogger("runefoble.game_session.campaign")

SpiceDB = SpiceDBClient | MockSpiceDBClient
MEMBER_RELATIONS = ("player", "spectator", "dungeon_master", "game_master")


async def _guarded(action: str, call: Callable[[], Awaitable[Any]]) -> None:
    try:
        await call()
    except Exception as exc:
        logger.exception("SpiceDB %s failed", action)
        raise AuthorizationStoreError(
            "Authorization store is unavailable. Retry the request."
        ) from exc


async def grant_owner(spicedb: SpiceDB, campaign_id: str, owner_id: str) -> None:
    await _guarded(
        "owner write",
        lambda: spicedb.write_relationship("campaign", campaign_id, "owner", "user", owner_id),
    )


async def grant_member(spicedb: SpiceDB, campaign_id: str, role: str, user_id: str) -> None:
    relation = "spectator" if role == "spectator" else "player"
    await _guarded(
        "member write",
        lambda: spicedb.write_relationship("campaign", campaign_id, relation, "user", user_id),
    )


async def revoke_member(spicedb: SpiceDB, campaign_id: str, user_id: str) -> None:
    for relation in MEMBER_RELATIONS:
        await _guarded(
            "member delete",
            lambda rel=relation: spicedb.delete_relationship(
                "campaign", campaign_id, rel, "user", user_id
            ),
        )


async def link_session(spicedb: SpiceDB, session_id: str, campaign_id: str) -> None:
    """Link a session to its campaign for both the session and game_session object types."""
    for object_type in ("session", "game_session"):
        await _guarded(
            "session link write",
            lambda t=object_type: spicedb.write_relationship(
                t, session_id, "campaign", "campaign", campaign_id
            ),
        )
