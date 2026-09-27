"""Tests for Caravan Aggregate and Contract Models Modular Decomposition.

Part of TASK-0186 / PRD-0007 / US-0058 / ADR-0003 / ADR-0007 / ADR-0011.
Governed by Hard Invariant 6 (File length limits) and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from game_session.caravan import (
    CaravanContractAggregate,
    CaravanContractState,
)
from game_session.caravan.escrow import (
    apply_ambush_stats_to_stock,
    apply_delivery_success_to_stock,
    ensure_outpost_stock_entry,
    filter_contracts,
    generate_default_refined_stock,
)
from game_session.caravan.models import (
    _to_uuid,
)
from game_session.caravan.transit import (
    calculate_contract_payout,
    calculate_transit_ambush_progress,
    validate_ambush_outcome,
    validate_can_accept,
    validate_can_dispatch,
    validate_can_fulfill,
    validate_contract_post,
)
from game_session.caravan_ledger import (
    CaravanLedgerAggregate,
    CaravanLedgerState,
    calculate_economic_price_modifier,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CARAVAN_DIR = REPO_ROOT / "services" / "game_session" / "src" / "game_session" / "caravan"


def test_caravan_file_length_invariants():
    """Verify all caravan source files respect strict length bounds under Hard Invariant 6."""
    caravan_facade = CARAVAN_DIR.parent / "caravan.py"
    ledger_facade = CARAVAN_DIR.parent / "caravan_ledger.py"

    assert caravan_facade.is_file()
    assert ledger_facade.is_file()

    # Facade files must be strictly < 60 lines
    caravan_lines = len(caravan_facade.read_text(encoding="utf-8").splitlines())
    ledger_lines = len(ledger_facade.read_text(encoding="utf-8").splitlines())
    assert caravan_lines < 60, f"caravan.py has {caravan_lines} lines (expected < 60)"
    assert ledger_lines < 60, f"caravan_ledger.py has {ledger_lines} lines (expected < 60)"

    # All submodule files under caravan/ must be strictly < 150 lines
    submodules = [path for path in CARAVAN_DIR.glob("*.py") if not path.name.startswith("__")]
    assert len(submodules) >= 6, "Expected at least 6 modular submodules in caravan/"

    for path in CARAVAN_DIR.glob("*.py"):
        lines = len(path.read_text(encoding="utf-8").splitlines())
        assert lines < 150, f"{path.name} has {lines} lines (must be strictly < 150 lines)"


def test_caravan_models_and_uuid_helpers():
    """Verify CaravanContractState and CaravanLedgerState initialization and UUID helpers."""
    state = CaravanContractState(contract_id="c-123")
    assert state.contract_id == "c-123"
    assert state.status == "open"

    ledger_state = CaravanLedgerState(shared_world_id="w-123")
    assert ledger_state.shared_world_id == "w-123"
    assert ledger_state.outpost_stocks == {}

    test_uid = uuid4()
    assert _to_uuid(str(test_uid)) == test_uid
    assert _to_uuid(test_uid) == test_uid
    assert _to_uuid("") is None
    assert _to_uuid("not-a-uuid") is None


def test_caravan_contract_lifecycle_and_events():
    """Verify CaravanContractAggregate event sourcing and transit stage transitions."""
    agg = CaravanContractAggregate()
    wid = uuid4()
    camp_poster = uuid4()
    camp_contractor = uuid4()

    # Post contract
    contract_id = agg.post_contract(
        shared_world_id=wid,
        origin_outpost="haven_outpost",
        destination_outpost="iron_citadel",
        cargo={"timber": 10, "iron_ore": 5},
        cargo_value=300,
        posted_by_campaign_id=camp_poster,
        route_risk_level="high",
        transit_stages=3,
        escort_collateral=60,
        reward_gold=200,
        reward_reputation=15,
    )
    assert agg.state.status == "open"
    assert agg.state.contract_id == contract_id
    assert agg.state.origin_outpost == "haven_outpost"
    assert agg.state.transit_stages == 3

    # Accept contract
    agg.accept_contract(
        contractor_campaign_id=camp_contractor,
        contractor_party_name="Iron Vanguard",
        accepted_by_user_id="user-mercenary",
    )
    assert agg.state.status == "accepted"
    assert agg.state.contractor_party_name == "Iron Vanguard"

    # Dispatch caravan
    caravan_id = agg.dispatch_caravan()
    assert agg.state.status == "in_transit"
    assert agg.state.caravan_id == caravan_id
    assert agg.state.current_stage == 1

    # Ambush at stage 1: cargo damaged
    agg.report_ambush_outcome(
        stage_index=1,
        ambush_type="goblin_ambush",
        danger_level=2,
        outcome="cargo_damaged",
        cargo_loss_percentage=0.2,
    )
    assert agg.state.status == "in_transit"
    assert agg.state.cargo_loss_percentage == 0.2
    assert agg.state.current_stage == 2

    # Fulfill contract at destination
    payout = agg.fulfill_contract()
    assert agg.state.status == "fulfilled"
    assert payout["cargo_delivered"]["timber"] == 8
    assert payout["cargo_delivered"]["iron_ore"] == 4
    assert payout["cargo_value_delivered"] == 240
    assert payout["reward_gold_paid"] > 0
    assert payout["reputation_awarded"] > 0
    assert len(agg.uncommitted_events) == 5


def test_caravan_ledger_stock_and_economy():
    """Verify CaravanLedgerAggregate trade deliveries, stock unlocks, and price modifiers."""
    wid = uuid4()
    ledger = CaravanLedgerAggregate(wid)
    camp_id = uuid4()

    # Dispatch trade caravan
    caravan_id = ledger.dispatch_caravan(
        origin_outpost="haven_outpost",
        destination_outpost="frontier_bastion",
        cargo={"silver_ore": 4, "healing_herbs": 6},
        dispatched_by_campaign_id=camp_id,
        transit_turns=2,
    )
    assert caravan_id in ledger.state.caravans
    assert ledger.state.caravans[caravan_id]["status"] == "in_transit"

    # Complete trade arrival
    result = ledger.complete_caravan_trade(caravan_id=caravan_id)
    assert result["status"] == "completed"

    stock = ledger.state.outpost_stocks.get("frontier_bastion")
    assert stock is not None
    assert stock["workshop_reagents"]["silver_ore"] == 4
    assert stock["delivery_stats"]["total_deliveries"] == 1
    assert stock["delivery_stats"]["successful_deliveries"] == 1
    assert stock["price_modifier"] == 1.0


def test_transit_calculations_and_validations():
    """Verify extracted transit stage calculation and validation functions."""
    # Posting validation
    with pytest.raises(ValueError, match="Origin and destination outposts must be distinct"):
        validate_contract_post("Haven", "haven", {"ore": 1}, 100)  # case-insensitive check
    with pytest.raises(ValueError, match="at least one item"):
        validate_contract_post("Haven", "Outpost", {}, 100)
    with pytest.raises(ValueError, match="greater than zero"):
        validate_contract_post("Haven", "Outpost", {"ore": 1}, 0)

    # State transition validations
    with pytest.raises(ValueError, match="Cannot accept"):
        validate_can_accept("fulfilled")
    with pytest.raises(ValueError, match="Cannot dispatch"):
        validate_can_dispatch("open")
    with pytest.raises(ValueError, match="Cannot report ambush"):
        validate_ambush_outcome("fulfilled", "repelled")
    with pytest.raises(ValueError, match="Invalid ambush outcome"):
        validate_ambush_outcome("in_transit", "unrecognized_outcome")
    with pytest.raises(ValueError, match="must be in transit"):
        validate_can_fulfill("open")

    # Ambush stage progression calculations
    status, stage, loss = calculate_transit_ambush_progress(
        current_stage=1,
        transit_stages=3,
        stage_index=1,
        outcome="caravan_destroyed",
        current_loss_pct=0.1,
        reported_loss_pct=0.5,
    )
    assert status == "failed"
    assert loss == 1.0

    status, stage, loss = calculate_transit_ambush_progress(
        current_stage=1,
        transit_stages=3,
        stage_index=1,
        outcome="repelled",
        current_loss_pct=0.0,
        reported_loss_pct=0.0,
    )
    assert status == "in_transit"
    assert stage == 2
    assert loss == 0.0

    # Contract payout calculation
    payout = calculate_contract_payout(
        cargo={"ore": 10},
        cargo_value=100,
        reward_gold=50,
        escort_collateral=20,
        reward_reputation=10,
        cargo_loss_percentage=0.5,
    )
    assert payout["cargo_delivered"]["ore"] == 5
    assert payout["cargo_value_delivered"] == 50
    assert payout["reward_gold_paid"] == int(round(50 * (1.0 - 0.25))) + 20
    assert payout["reputation_awarded"] == 5


def test_escrow_pricing_and_filtering():
    """Verify economic price modifier calculations and notice board contract filtering."""
    # Pricing modifiers
    assert calculate_economic_price_modifier(0, 0) == 1.0
    assert calculate_economic_price_modifier(2, 2) == 0.90  # abundance discount
    assert calculate_economic_price_modifier(5, 1) > 1.0  # scarcity surcharge

    # Escrow helpers
    stocks: dict[str, dict] = {}
    entry = ensure_outpost_stock_entry(stocks, "Outpost_A")
    assert entry["price_modifier"] == 1.0

    refined = generate_default_refined_stock({"timber": 3})
    assert "refined_timber" in refined
    assert refined["refined_timber"]["quantity"] == 6

    apply_delivery_success_to_stock(entry, "caravan-1", {"timber": 3}, {"refined_timber": 6})
    assert entry["workshop_reagents"]["timber"] == 3

    apply_ambush_stats_to_stock(entry, "caravan_destroyed")
    assert entry["delivery_stats"]["ambushed_deliveries"] == 1

    # Contract filtering
    contracts = {
        "c1": {
            "route_risk_level": "low",
            "destination_outpost": "Haven",
            "status": "open",
            "reward_gold": 100,
        },
        "c2": {
            "route_risk_level": "deadly",
            "destination_outpost": "Citadel",
            "status": "open",
            "reward_gold": 500,
        },
        "c3": {
            "route_risk_level": "deadly",
            "destination_outpost": "Citadel",
            "status": "fulfilled",
            "reward_gold": 500,
        },
    }

    assert len(filter_contracts(contracts, status="open")) == 2
    assert len(filter_contracts(contracts, risk_level="deadly", status="open")) == 1
    assert len(filter_contracts(contracts, destination="citadel", min_reward=600)) == 0
