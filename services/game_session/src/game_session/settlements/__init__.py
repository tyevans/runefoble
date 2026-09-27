"""Cross-Campaign Settlement and Haven Registry bounded context."""

from game_session.settlements.aggregate import SettlementAggregate
from game_session.settlements.auth import (
    check_settlement_permission,
    check_world_charter_permission,
    register_campaign_haven_discovery,
    write_settlement_relationships,
)
from game_session.settlements.models import (
    DEFAULT_FACILITIES,
    FACILITY_REST_BOONS,
    FACILITY_TIER_NAMES,
    CharterSettlementRequest,
    ClaimRestBoonRequest,
    SettlementState,
    UpgradeFacilityRequest,
)

__all__ = [
    "DEFAULT_FACILITIES",
    "FACILITY_REST_BOONS",
    "FACILITY_TIER_NAMES",
    "CharterSettlementRequest",
    "ClaimRestBoonRequest",
    "SettlementAggregate",
    "SettlementState",
    "UpgradeFacilityRequest",
    "check_settlement_permission",
    "check_world_charter_permission",
    "register_campaign_haven_discovery",
    "write_settlement_relationships",
]
