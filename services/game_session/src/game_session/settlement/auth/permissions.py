"""SpiceDB Zanzibar authorization helpers for settlements and establishments.

Governed by ADR-0001 (Zanzibar Fine-Grained Authorization) and Hard Invariant 1.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException


async def _enforce(
    spicedb: Any, res: str, rid: str, perms: list[str], uid: str | None, verb: str
) -> None:
    if uid:
        for p in perms:
            if await spicedb.check_permission(res, str(rid), p, "user", str(uid)):
                return
        err = f"Permission denied: subject '{uid}' {verb} {res}:{rid}"
        raise HTTPException(status_code=403, detail=err)


async def check_campaign_write_permission(
    spicedb: Any, campaign_id: str, user_id: str | None
) -> None:
    """Ensure user has campaign play or GM permissions to construct settlements."""
    p = ["play", "run_session", "manage"]
    await _enforce(spicedb, "campaign", campaign_id, p, user_id, "lacks write permission on")


async def check_settlement_read_permission(
    spicedb: Any, settlement_id: str, user_id: str | None
) -> None:
    """Ensure user has permission to view settlement."""
    await _enforce(spicedb, "settlement", settlement_id, ["view"], user_id, "cannot view")


async def check_settlement_write_permission(
    spicedb: Any, settlement_id: str, user_id: str | None
) -> None:
    """Ensure user has permission to upgrade or build in settlement."""
    p = ["upgrade", "manage"]
    await _enforce(spicedb, "settlement", settlement_id, p, user_id, "cannot construct/upgrade in")


async def check_establishment_read_permission(
    spicedb: Any, establishment_id: str, user_id: str | None
) -> None:
    """Ensure user has permission to view establishment."""
    await _enforce(spicedb, "establishment", establishment_id, ["view"], user_id, "cannot view")


async def check_establishment_write_permission(
    spicedb: Any, establishment_id: str, user_id: str | None
) -> None:
    """Ensure user has permission to manage/upgrade establishment."""
    p = ["manage", "edit"]
    await _enforce(spicedb, "establishment", establishment_id, p, user_id, "cannot manage")


async def check_establishment_play_permission(
    spicedb: Any, establishment_id: str, user_id: str | None
) -> bool:
    """Ensure user has permission to play minigames / patronize establishment."""
    if not user_id:
        return True
    for p in ("play", "view", "manage"):
        if await spicedb.check_permission(
            "establishment", str(establishment_id), p, "user", str(user_id)
        ):
            return True
    return False


async def check_npc_read_permission(spicedb: Any, npc_id: str, user_id: str | None) -> None:
    """Ensure user has permission to view worker profile."""
    await _enforce(spicedb, "npc", npc_id, ["view"], user_id, "cannot view")


async def check_npc_write_permission(spicedb: Any, npc_id: str, user_id: str | None) -> None:
    """Ensure user has permission to manage worker or edit temperament state."""
    p = ["edit_mood", "manage"]
    await _enforce(spicedb, "npc", npc_id, p, user_id, "cannot manage")


async def check_negotiation_read_permission(
    spicedb: Any, negotiation_id: str, user_id: str | None
) -> None:
    """Ensure user has permission to view negotiation state and barks."""
    await _enforce(spicedb, "negotiation", negotiation_id, ["view"], user_id, "cannot view")


async def check_negotiation_participate_permission(
    spicedb: Any, negotiation_id: str, user_id: str | None
) -> None:
    """Ensure user has permission to participate in negotiation and submit gambits."""
    await _enforce(
        spicedb, "negotiation", negotiation_id, ["participate"], user_id, "cannot participate in"
    )


async def check_negotiation_arbitrate_permission(
    spicedb: Any, negotiation_id: str, user_id: str | None
) -> None:
    """Ensure user has DM or manager authority to arbitrate negotiation terms and moods."""
    p = ["arbitrate", "manage"]
    await _enforce(
        spicedb, "negotiation", negotiation_id, p, user_id, "lacks DM arbitration rights on"
    )


__all__ = [
    "check_campaign_write_permission",
    "check_establishment_play_permission",
    "check_establishment_read_permission",
    "check_establishment_write_permission",
    "check_negotiation_arbitrate_permission",
    "check_negotiation_participate_permission",
    "check_negotiation_read_permission",
    "check_npc_read_permission",
    "check_npc_write_permission",
    "check_settlement_read_permission",
    "check_settlement_write_permission",
]
