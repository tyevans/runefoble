"""Tests for game_session settlement and facility domain models."""

from __future__ import annotations

from game_session.models import (
    DEFAULT_FACILITIES,
    FACILITY_REST_BOONS,
    FACILITY_TIER_NAMES,
    CharterSettlementRequest,
    ClaimRestBoonRequest,
    SettlementState,
    UpgradeFacilityRequest,
)


def test_settlement_exports_and_imports() -> None:
    """Verify re-exports and direct submodule imports for settlement models."""
    from game_session.models.settlement import SettlementState as DirectSettlementState

    assert DirectSettlementState is SettlementState
    items = (
        CharterSettlementRequest,
        UpgradeFacilityRequest,
        ClaimRestBoonRequest,
        DEFAULT_FACILITIES,
        FACILITY_REST_BOONS,
        FACILITY_TIER_NAMES,
    )
    assert all(item is not None for item in items)


def test_settlement_state_initialization_and_defaults() -> None:
    """Verify default facilities, tier configuration, and state fields."""
    settlement = SettlementState(
        settlement_id="haven-1",
        name="Wolfstone Outpost",
        settlement_type="outpost",
    )
    assert settlement.level == 1
    assert "workshop" in settlement.facilities
    assert "sanctum" in settlement.facilities
    assert "fortifications" in settlement.facilities
    assert "watchtower" in settlement.facilities
    assert settlement.facilities["workshop"] == 1


def test_settlement_requests_validation() -> None:
    """Verify request validation for chartering, facility upgrade, and rest boons."""
    charter_req = CharterSettlementRequest(
        name="New Haven",
        shared_world_id="sw-1",
        settlement_type="fortress",
        founded_by_campaign_id="camp-1",
    )
    assert charter_req.name == "New Haven"
    assert charter_req.shared_world_id == "sw-1"
    assert charter_req.settlement_type == "fortress"

    upgrade_req = UpgradeFacilityRequest(facility_id="workshop", gold_spent=100)
    assert upgrade_req.facility_id == "workshop"
    assert upgrade_req.gold_spent == 100

    claim_req = ClaimRestBoonRequest(
        campaign_id="camp-1", facility_id="sanctum", character_id="char-1"
    )
    assert claim_req.facility_id == "sanctum"
    assert claim_req.campaign_id == "camp-1"


def test_settlement_constants() -> None:
    """Verify settlement default facilities, rest boons, and tier mappings."""
    assert "workshop" in DEFAULT_FACILITIES
    assert "sanctum" in FACILITY_REST_BOONS
    assert "workshop" in FACILITY_TIER_NAMES
    assert 1 in FACILITY_TIER_NAMES["workshop"]
