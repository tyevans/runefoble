"""SpiceDB Zanzibar relationship tuple writers for settlements and establishments.

Governed by ADR-0001 (Zanzibar Fine-Grained Authorization) and Hard Invariant 1.
"""

from __future__ import annotations

from typing import Any


async def _rel(spicedb: Any, rtype: str, rid: str, rel: str, stype: str, sid: str | None) -> None:
    if sid:
        await spicedb.write_relationship(rtype, str(rid), rel, stype, str(sid))


async def write_settlement_relationships(
    spicedb: Any,
    settlement_id: str,
    campaign_id: str | None = None,
    founder_id: str | None = None,
    shared_world_id: str | None = None,
) -> None:
    """Write SpiceDB Zanzibar tuples for settlement haven."""
    sid = str(settlement_id)
    await _rel(spicedb, "settlement", sid, "campaign", "campaign", campaign_id)
    await _rel(spicedb, "settlement", sid, "discovering_campaign", "campaign", campaign_id)
    await _rel(spicedb, "settlement", sid, "founder", "user", founder_id)
    await _rel(spicedb, "settlement", sid, "shared_world", "shared_world", shared_world_id)


async def write_establishment_relationships(
    spicedb: Any,
    establishment_id: str,
    settlement_id: str,
    campaign_id: str | None = None,
    owner_id: str | None = None,
) -> None:
    """Write SpiceDB Zanzibar tuples for establishment storefront."""
    eid = str(establishment_id)
    await _rel(spicedb, "establishment", eid, "settlement", "settlement", settlement_id)
    await _rel(spicedb, "establishment", eid, "campaign", "campaign", campaign_id)
    await _rel(spicedb, "establishment", eid, "owner", "user", owner_id)


async def write_npc_relationships(
    spicedb: Any,
    npc_id: str,
    establishment_id: str | None = None,
    campaign_id: str | None = None,
    manager_id: str | None = None,
) -> None:
    """Write SpiceDB Zanzibar tuples for assigned NPC worker."""
    nid = str(npc_id)
    await _rel(spicedb, "npc", nid, "establishment", "establishment", establishment_id)
    await _rel(spicedb, "npc", nid, "campaign", "campaign", campaign_id)
    await _rel(spicedb, "npc", nid, "manager", "user", manager_id)


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
    await _rel(spicedb, "negotiation", nid, "establishment", "establishment", establishment_id)
    await _rel(spicedb, "negotiation", nid, "campaign", "campaign", campaign_id)
    await _rel(spicedb, "negotiation", nid, "session", "session", session_id)
    await _rel(spicedb, "negotiation", nid, "participant", "user", participant_id)
    await _rel(spicedb, "negotiation", nid, "arbitrator", "user", arbitrator_id)


__all__ = [
    "write_establishment_relationships",
    "write_negotiation_relationships",
    "write_npc_relationships",
    "write_settlement_relationships",
]
