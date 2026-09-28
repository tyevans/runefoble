"""SpiceDB Zanzibar authorization helpers for settlements and establishments.

Governed by ADR-0001 (Zanzibar Fine-Grained Authorization) and Hard Invariant 1.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException


async def check_campaign_write_permission(
    spicedb: Any,
    campaign_id: str,
    user_id: str | None,
) -> None:
    """Ensure user has campaign play or GM permissions to construct settlements."""
    if not user_id:
        return
    allowed = (
        await spicedb.check_permission("campaign", str(campaign_id), "play", "user", str(user_id))
        or await spicedb.check_permission(
            "campaign", str(campaign_id), "run_session", "user", str(user_id)
        )
        or await spicedb.check_permission(
            "campaign", str(campaign_id), "manage", "user", str(user_id)
        )
    )
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: subject '{user_id}' lacks write permission on campaign:{campaign_id}",
        )


async def check_settlement_read_permission(
    spicedb: Any,
    settlement_id: str,
    user_id: str | None,
) -> None:
    """Ensure user has permission to view settlement."""
    if not user_id:
        return
    allowed = await spicedb.check_permission(
        "settlement", str(settlement_id), "view", "user", str(user_id)
    )
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: subject '{user_id}' cannot view settlement:{settlement_id}",
        )


async def check_settlement_write_permission(
    spicedb: Any,
    settlement_id: str,
    user_id: str | None,
) -> None:
    """Ensure user has permission to upgrade or build in settlement."""
    if not user_id:
        return
    allowed = await spicedb.check_permission(
        "settlement", str(settlement_id), "upgrade", "user", str(user_id)
    ) or await spicedb.check_permission(
        "settlement", str(settlement_id), "manage", "user", str(user_id)
    )
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: subject '{user_id}' cannot construct/upgrade in settlement:{settlement_id}",
        )


async def check_establishment_read_permission(
    spicedb: Any,
    establishment_id: str,
    user_id: str | None,
) -> None:
    """Ensure user has permission to view establishment."""
    if not user_id:
        return
    allowed = await spicedb.check_permission(
        "establishment", str(establishment_id), "view", "user", str(user_id)
    )
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: subject '{user_id}' cannot view establishment:{establishment_id}",
        )


async def check_establishment_write_permission(
    spicedb: Any,
    establishment_id: str,
    user_id: str | None,
) -> None:
    """Ensure user has permission to manage/upgrade establishment."""
    if not user_id:
        return
    allowed = await spicedb.check_permission(
        "establishment", str(establishment_id), "manage", "user", str(user_id)
    ) or await spicedb.check_permission(
        "establishment", str(establishment_id), "edit", "user", str(user_id)
    )
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: subject '{user_id}' cannot manage establishment:{establishment_id}",
        )


async def check_establishment_play_permission(
    spicedb: Any,
    establishment_id: str,
    user_id: str | None,
) -> bool:
    """Ensure user has permission to play minigames / patronize establishment."""
    if not user_id:
        return True
    return bool(
        await spicedb.check_permission(
            "establishment", str(establishment_id), "play", "user", str(user_id)
        )
        or await spicedb.check_permission(
            "establishment", str(establishment_id), "view", "user", str(user_id)
        )
        or await spicedb.check_permission(
            "establishment", str(establishment_id), "manage", "user", str(user_id)
        )
    )


async def write_settlement_relationships(
    spicedb: Any,
    settlement_id: str,
    campaign_id: str | None = None,
    founder_id: str | None = None,
    shared_world_id: str | None = None,
) -> None:
    """Write SpiceDB Zanzibar tuples for settlement haven."""
    sid = str(settlement_id)
    if campaign_id:
        await spicedb.write_relationship(
            resource_type="settlement",
            resource_id=sid,
            relation="campaign",
            subject_type="campaign",
            subject_id=str(campaign_id),
        )
        await spicedb.write_relationship(
            resource_type="settlement",
            resource_id=sid,
            relation="discovering_campaign",
            subject_type="campaign",
            subject_id=str(campaign_id),
        )
    if founder_id:
        await spicedb.write_relationship(
            resource_type="settlement",
            resource_id=sid,
            relation="founder",
            subject_type="user",
            subject_id=str(founder_id),
        )
    if shared_world_id:
        await spicedb.write_relationship(
            resource_type="settlement",
            resource_id=sid,
            relation="shared_world",
            subject_type="shared_world",
            subject_id=str(shared_world_id),
        )


async def write_establishment_relationships(
    spicedb: Any,
    establishment_id: str,
    settlement_id: str,
    campaign_id: str | None = None,
    owner_id: str | None = None,
) -> None:
    """Write SpiceDB Zanzibar tuples for establishment storefront."""
    eid = str(establishment_id)
    await spicedb.write_relationship(
        resource_type="establishment",
        resource_id=eid,
        relation="settlement",
        subject_type="settlement",
        subject_id=str(settlement_id),
    )
    if campaign_id:
        await spicedb.write_relationship(
            resource_type="establishment",
            resource_id=eid,
            relation="campaign",
            subject_type="campaign",
            subject_id=str(campaign_id),
        )
    if owner_id:
        await spicedb.write_relationship(
            resource_type="establishment",
            resource_id=eid,
            relation="owner",
            subject_type="user",
            subject_id=str(owner_id),
        )
