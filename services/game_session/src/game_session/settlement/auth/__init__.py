"""Modular settlement authentication and Zanzibar permissions package.

Governed by ADR-0001, ADR-0003, ADR-0005, ADR-0007, and ADR-0013.
"""

from __future__ import annotations

from game_session.settlement.auth.dependencies import (
    require_establishment_manager,
    require_haven_builder,
    require_haven_viewer,
)
from game_session.settlement.auth.permissions import (
    check_campaign_write_permission,
    check_establishment_read_permission,
    check_establishment_write_permission,
    check_negotiation_arbitrate_permission,
    check_negotiation_participate_permission,
    check_negotiation_read_permission,
    check_npc_read_permission,
    check_npc_write_permission,
    check_settlement_permission,
    check_settlement_read_permission,
    check_settlement_write_permission,
    check_world_charter_permission,
)
from game_session.settlement.auth.relationships import (
    register_campaign_haven_discovery,
    write_establishment_relationships,
    write_negotiation_relationships,
    write_npc_relationships,
    write_settlement_relationships,
)
from runefoble_auth.principal import VerifiedPrincipal

__all__ = [
    "VerifiedPrincipal",
    "check_campaign_write_permission",
    "check_establishment_read_permission",
    "check_establishment_write_permission",
    "check_negotiation_arbitrate_permission",
    "check_negotiation_participate_permission",
    "check_negotiation_read_permission",
    "check_npc_read_permission",
    "check_npc_write_permission",
    "check_settlement_read_permission",
    "check_settlement_write_permission",
    "require_establishment_manager",
    "require_haven_builder",
    "require_haven_viewer",
    "check_settlement_permission",
    "check_world_charter_permission",
    "register_campaign_haven_discovery",
    "write_establishment_relationships",
    "write_negotiation_relationships",
    "write_npc_relationships",
    "write_settlement_relationships",
]
