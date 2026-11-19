"""Child index kinds and list queries of the settlement domain (TASK-0567, ADR-0021 D2).

The kind values are part of the index stream ids. Do not change them.
"""

from __future__ import annotations

from enum import StrEnum

from game_session.shared.child_index_queries import list_child_ids


class SettlementChildIndex(StrEnum):
    """Parent-to-child lists whose parent the settlement domain owns or reads."""

    SETTLEMENT_ESTABLISHMENTS = "settlement_establishments"
    CAMPAIGN_SETTLEMENTS = "campaign_settlements"
    ESTABLISHMENT_WORKERS = "establishment_workers"
    ESTABLISHMENT_NEGOTIATIONS = "establishment_negotiations"


async def list_establishments_for_settlement(settlement_id: str) -> list[str]:
    """Return the establishment ids built in one settlement."""
    return await list_child_ids(SettlementChildIndex.SETTLEMENT_ESTABLISHMENTS, settlement_id)


async def list_settlements_for_campaign(campaign_id: str) -> list[str]:
    """Return the settlement ids founded for one campaign."""
    return await list_child_ids(SettlementChildIndex.CAMPAIGN_SETTLEMENTS, campaign_id)


async def list_workers_for_establishment(establishment_id: str) -> list[str]:
    """Return the NPC worker ids assigned to one establishment."""
    return await list_child_ids(SettlementChildIndex.ESTABLISHMENT_WORKERS, establishment_id)


__all__ = [
    "SettlementChildIndex",
    "list_establishments_for_settlement",
    "list_settlements_for_campaign",
    "list_workers_for_establishment",
]
