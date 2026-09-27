"""SpiceDB Zanzibar authorization helpers for settlements and havens.

Governed by ADR-0001 (Zanzibar Fine-Grained Authorization) and Hard Invariant 1.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException


async def write_settlement_relationships(
    spicedb: Any,
    settlement_id: str,
    shared_world_id: str,
    founder_id: str | None = None,
    campaign_id: str | None = None,
) -> None:
    """Establish Zanzibar relationships linking settlement to shared world, founder, and campaign."""
    sid = str(settlement_id)
    wid = str(shared_world_id)
    await spicedb.write_relationship(
        resource_type="settlement",
        resource_id=sid,
        relation="shared_world",
        subject_type="shared_world",
        subject_id=wid,
    )
    if founder_id:
        await spicedb.write_relationship(
            resource_type="settlement",
            resource_id=sid,
            relation="founder",
            subject_type="user",
            subject_id=str(founder_id),
        )
    if campaign_id:
        await spicedb.write_relationship(
            resource_type="settlement",
            resource_id=sid,
            relation="discovering_campaign",
            subject_type="campaign",
            subject_id=str(campaign_id),
        )


async def register_campaign_haven_discovery(
    spicedb: Any,
    settlement_id: str,
    campaign_id: str,
) -> None:
    """Register an adventuring campaign as having discovered/unlocked a haven."""
    await spicedb.write_relationship(
        resource_type="settlement",
        resource_id=str(settlement_id),
        relation="discovering_campaign",
        subject_type="campaign",
        subject_id=str(campaign_id),
    )


async def check_settlement_permission(
    spicedb: Any,
    settlement_id: str,
    perm: str,
    user_id: str | None,
) -> None:
    """Enforce Zanzibar permission check on settlement resource."""
    if not user_id:
        return
    allowed = await spicedb.check_permission(
        "settlement", str(settlement_id), perm, "user", str(user_id)
    )
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: subject '{user_id}' lacks '{perm}' on settlement:{settlement_id}",
        )


async def check_world_charter_permission(
    spicedb: Any,
    shared_world_id: str,
    user_id: str | None,
) -> None:
    """Ensure user has discovery or trade permissions on the shared world to charter a haven."""
    if not user_id:
        return
    allowed = (
        await spicedb.check_permission(
            "shared_world", str(shared_world_id), "discover", "user", str(user_id)
        )
        or await spicedb.check_permission(
            "shared_world", str(shared_world_id), "manage", "user", str(user_id)
        )
        or await spicedb.check_permission(
            "shared_world", str(shared_world_id), "trade", "user", str(user_id)
        )
    )
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: subject '{user_id}' cannot charter havens in shared_world:{shared_world_id}",
        )
