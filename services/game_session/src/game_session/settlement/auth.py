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


async def check_npc_read_permission(
    spicedb: Any,
    npc_id: str,
    user_id: str | None,
) -> None:
    """Ensure user has permission to view worker profile."""
    if not user_id:
        return
    allowed = await spicedb.check_permission("npc", str(npc_id), "view", "user", str(user_id))
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: subject '{user_id}' cannot view npc:{npc_id}",
        )


async def check_npc_write_permission(
    spicedb: Any,
    npc_id: str,
    user_id: str | None,
) -> None:
    """Ensure user has permission to manage worker or edit temperament state."""
    if not user_id:
        return
    allowed = await spicedb.check_permission(
        "npc", str(npc_id), "edit_mood", "user", str(user_id)
    ) or await spicedb.check_permission("npc", str(npc_id), "manage", "user", str(user_id))
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: subject '{user_id}' cannot manage npc:{npc_id}",
        )


async def write_npc_relationships(
    spicedb: Any,
    npc_id: str,
    establishment_id: str | None = None,
    campaign_id: str | None = None,
    manager_id: str | None = None,
) -> None:
    """Write SpiceDB Zanzibar tuples for assigned NPC worker."""
    nid = str(npc_id)
    if establishment_id:
        await spicedb.write_relationship(
            resource_type="npc",
            resource_id=nid,
            relation="establishment",
            subject_type="establishment",
            subject_id=str(establishment_id),
        )
    if campaign_id:
        await spicedb.write_relationship(
            resource_type="npc",
            resource_id=nid,
            relation="campaign",
            subject_type="campaign",
            subject_id=str(campaign_id),
        )
    if manager_id:
        await spicedb.write_relationship(
            resource_type="npc",
            resource_id=nid,
            relation="manager",
            subject_type="user",
            subject_id=str(manager_id),
        )


async def check_negotiation_read_permission(
    spicedb: Any,
    negotiation_id: str,
    user_id: str | None,
) -> None:
    """Ensure user has permission to view negotiation state and barks."""
    if not user_id:
        return
    allowed = await spicedb.check_permission(
        "negotiation", str(negotiation_id), "view", "user", str(user_id)
    )
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: subject '{user_id}' cannot view negotiation:{negotiation_id}",
        )


async def check_negotiation_participate_permission(
    spicedb: Any,
    negotiation_id: str,
    user_id: str | None,
) -> None:
    """Ensure user has permission to participate in negotiation and submit gambits."""
    if not user_id:
        return
    allowed = await spicedb.check_permission(
        "negotiation", str(negotiation_id), "participate", "user", str(user_id)
    )
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: subject '{user_id}' cannot participate in negotiation:{negotiation_id}",
        )


async def check_negotiation_arbitrate_permission(
    spicedb: Any,
    negotiation_id: str,
    user_id: str | None,
) -> None:
    """Ensure user has DM or manager authority to arbitrate negotiation terms and moods."""
    if not user_id:
        return
    allowed = await spicedb.check_permission(
        "negotiation", str(negotiation_id), "arbitrate", "user", str(user_id)
    ) or await spicedb.check_permission(
        "negotiation", str(negotiation_id), "manage", "user", str(user_id)
    )
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: subject '{user_id}' lacks DM arbitration rights on negotiation:{negotiation_id}",
        )


async def write_negotiation_relationships(
    spicedb: Any,
    negotiation_id: str,
    establishment_id: str | None = None,
    campaign_id: str | None = None,
    session_id: str | None = None,
    participant_id: str | None = None,
    arbitrator_id: str | None = None,
) -> None:
    """Write SpiceDB Zanzibar tuples for interactive negotiation session."""
    nid = str(negotiation_id)
    if establishment_id:
        await spicedb.write_relationship(
            resource_type="negotiation",
            resource_id=nid,
            relation="establishment",
            subject_type="establishment",
            subject_id=str(establishment_id),
        )
    if campaign_id:
        await spicedb.write_relationship(
            resource_type="negotiation",
            resource_id=nid,
            relation="campaign",
            subject_type="campaign",
            subject_id=str(campaign_id),
        )
    if session_id:
        await spicedb.write_relationship(
            resource_type="negotiation",
            resource_id=nid,
            relation="session",
            subject_type="session",
            subject_id=str(session_id),
        )
    if participant_id:
        await spicedb.write_relationship(
            resource_type="negotiation",
            resource_id=nid,
            relation="participant",
            subject_type="user",
            subject_id=str(participant_id),
        )
    if arbitrator_id:
        await spicedb.write_relationship(
            resource_type="negotiation",
            resource_id=nid,
            relation="arbitrator",
            subject_type="user",
            subject_id=str(arbitrator_id),
        )
