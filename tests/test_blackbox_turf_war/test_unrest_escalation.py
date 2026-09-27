"""Tests for regional unrest threshold triggers, riot states, and event publication.

Governed by ADR-0002, ADR-0006, and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from eventsource.domain.event_registry import get_event_class_or_none
from fastapi.testclient import TestClient
from runefoble_events import (
    FactionSkirmishResolved,
    FactionSkirmishResolvedEvent,
    FactionTerritoryCaptured,
    FactionTerritoryCapturedEvent,
    RegionalUnrestEscalated,
    RegionalUnrestEscalatedEvent,
)
from the_watcher.turf_war.unrest_calculator import UnrestCalculator

from .conftest import setup_campaign_roles


def test_cloudevents_registration():
    """Verify turf war domain events are registered and produce valid CloudEvents 1.0."""
    prefix = "runefoble.events.watcher"
    events = [
        (f"{prefix}.faction_skirmish_resolved", FactionSkirmishResolvedEvent),
        (f"{prefix}.faction_territory_captured", FactionTerritoryCapturedEvent),
        (f"{prefix}.regional_unrest_escalated", RegionalUnrestEscalatedEvent),
    ]
    for type_name, expected_cls in events:
        assert get_event_class_or_none(type_name) == expected_cls

    assert FactionSkirmishResolved == FactionSkirmishResolvedEvent
    assert FactionTerritoryCaptured == FactionTerritoryCapturedEvent
    assert RegionalUnrestEscalated == RegionalUnrestEscalatedEvent

    ev = FactionSkirmishResolvedEvent(
        skirmish_id="s1",
        campaign_id="c1",
        region_id="r1",
        contested_node="Tower",
        attacker_faction_id="f1",
        defender_faction_id="f2",
        winning_faction_id="f1",
        attacker_casualties=2,
        defender_casualties=8,
        territory_captured=True,
        unrest_delta=17,
        narrative="Breached.",
    )
    ce = ev.to_cloudevent_dict()
    assert ce["specversion"] == "1.0"
    assert ce["type"] == f"{prefix}.faction_skirmish_resolved"
    assert ce["data"]["territory_captured"] is True


@pytest.mark.asyncio
async def test_regional_unrest_progression_and_economic_friction(client: TestClient):
    """Verify progressive skirmishes push unrest into critical martial law and friction."""
    camp_id, dm_user, _ = await setup_campaign_roles()
    region_id = f"reg-{uuid4().hex[:8]}"

    for node, a_str, d_str in [("Gate", 40, 30), ("Square", 50, 35), ("Keep", 60, 40)]:
        client.post(
            "/the-watcher/factions/skirmish/simulate",
            json={
                "campaign_id": camp_id,
                "region_id": region_id,
                "contested_node": node,
                "attacker": {"faction_id": "f_atk", "military_strength": a_str},
                "defender": {"faction_id": "f_def", "military_strength": d_str},
                "terrain": "urban",
            },
            headers={"X-User-Id": dm_user},
        )

    res = client.get(
        f"/the-watcher/regions/{region_id}/unrest?campaign_id={camp_id}",
        headers={"X-User-Id": dm_user},
    )
    assert res.status_code == 200
    info = res.json()
    assert info["unrest_score"] >= 30
    assert len(info["contested_nodes"]) >= 2
    assert len(info["recent_skirmishes"]) == 3
    assert info["economic_friction"] > 0.2
    assert info["security_level"] in ["patrolled", "heightened", "curfew", "martial_law"]


def test_unrest_calculator_edge_cases():
    """Verify UnrestCalculator metrics, clamping, and peace stabilization decay."""
    calc = UnrestCalculator()
    levels = [(0, "calm"), (30, "guarded"), (60, "elevated"), (80, "high"), (95, "critical")]
    for score, lvl in levels:
        assert calc.calculate_alert_level(score) == lvl

    assert calc.calculate_security_level("calm") == "standard"
    assert calc.calculate_security_level("high") == "curfew"
    assert calc.calculate_security_level("critical") == "martial_law"
    assert calc.calculate_economic_friction(0) == 0.0
    assert calc.calculate_economic_friction(50) == 0.45
    assert calc.calculate_economic_friction(100) == 0.9
    assert calc.decay_unrest(50, peace_ticks=2, decay_per_tick=5) == 40
    assert calc.decay_unrest(5, peace_ticks=2, decay_per_tick=5) == 0
