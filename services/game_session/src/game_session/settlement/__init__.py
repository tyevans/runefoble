"""Settlement Haven Builder and Establishment domain package.

Governed by ADR-0001, ADR-0002, ADR-0007, ADR-0011, and PRD-0024.
"""

from __future__ import annotations

from game_session.settlement.auth import (
    check_campaign_write_permission,
    check_establishment_read_permission,
    check_establishment_write_permission,
    check_settlement_read_permission,
    check_settlement_write_permission,
    write_establishment_relationships,
    write_settlement_relationships,
)
from game_session.settlement.establishment_aggregate import EstablishmentAggregate
from game_session.settlement.models import (
    DEFAULT_FACILITIES,
    DEFAULT_TIER_DISTRICTS,
    FACILITY_REST_BOONS,
    FACILITY_TIER_NAMES,
    SCALE_MAX_DISTRICTS,
    SCALE_TO_TIER,
    TIER_MIN_PROSPERITY,
    TIER_TO_SCALE,
    ConstructEstablishmentRequest,
    EstablishmentCategory,
    EstablishmentState,
    FoundSettlementRequest,
    SettlementProjectionResponse,
    SettlementScale,
    SettlementState,
    UpgradeEstablishmentRequest,
    UpgradeSettlementTierRequest,
)
from game_session.settlement.settlement_aggregate import SettlementAggregate

__all__ = [
    "DEFAULT_FACILITIES",
    "DEFAULT_TIER_DISTRICTS",
    "EstablishmentAggregate",
    "EstablishmentCategory",
    "EstablishmentState",
    "FACILITY_REST_BOONS",
    "FACILITY_TIER_NAMES",
    "FoundSettlementRequest",
    "ConstructEstablishmentRequest",
    "SCALE_MAX_DISTRICTS",
    "SCALE_TO_TIER",
    "SettlementAggregate",
    "SettlementProjectionResponse",
    "SettlementScale",
    "SettlementState",
    "TIER_MIN_PROSPERITY",
    "TIER_TO_SCALE",
    "UpgradeEstablishmentRequest",
    "UpgradeSettlementTierRequest",
    "check_campaign_write_permission",
    "check_establishment_read_permission",
    "check_establishment_write_permission",
    "check_settlement_read_permission",
    "check_settlement_write_permission",
    "write_establishment_relationships",
    "write_settlement_relationships",
]
