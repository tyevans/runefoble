"""Blackbox tests: Campaign Analytics aggregates are computed from PostgreSQL read models.

Governed by ADR-0011 and Hard Invariant 7. Events enter through the Redis Streams transport.
Aggregates are read through the public heatmap, MVP, and timeline routes.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from runefoble_events.events import (
    CharacterHealthChanged,
    DiceRolled,
    InitiativeTurnAdvanced,
    SessionCreated,
    TokenPlaced,
)

from tests.helpers.campaign_analytics_service import (
    BOARD_STREAM,
    CHARACTER_STREAM,
    SESSION_STREAM,
    WATCHER_STREAM,
    AnalyticsService,
    wait_until,
)


def _heatmap_points(client: Any, cid: str) -> int:
    """Count the spatial rows of one campaign. /metrics counts the whole shared table."""
    body: dict[str, Any] = client.get(f"/api/v1/analytics/campaigns/{cid}/heatmap").json()
    return int(body["total_points"])


def _milestone_count(client: Any, cid: str) -> int:
    body: dict[str, Any] = client.get(f"/api/v1/analytics/campaigns/{cid}/timeline").json()
    return int(body["total_milestones"])


def _mvp(client: Any, cid: str) -> dict[str, Any]:
    body: dict[str, Any] = client.get(f"/api/v1/analytics/campaigns/{cid}/mvp").json()
    return body


def test_heatmap_buckets_movement_damage_and_knockout(analytics_service: AnalyticsService) -> None:
    """Movement, damage, and knockout at one tile aggregate into one heatmap cell."""
    cid, sid, tok = str(uuid4()), str(uuid4()), str(uuid4())
    analytics_service.grant_view(cid)

    with analytics_service.start() as client:
        analytics_service.publish(
            BOARD_STREAM,
            TokenPlaced(
                aggregate_id=sid,
                session_id=sid,
                campaign_id=cid,
                token_id=tok,
                name="Valeros",
                token_type="pc",
                x=12,
                y=18,
            ),
        )
        assert wait_until(lambda: _heatmap_points(client, cid) == 1)

        analytics_service.publish(
            CHARACTER_STREAM,
            CharacterHealthChanged(
                aggregate_id=tok,
                session_id=sid,
                campaign_id=cid,
                delta=-30,
                current_hp=10,
                max_hp=40,
            ),
        )
        analytics_service.publish(
            CHARACTER_STREAM,
            CharacterHealthChanged(
                aggregate_id=tok,
                session_id=sid,
                campaign_id=cid,
                delta=-10,
                current_hp=0,
                max_hp=40,
            ),
        )
        assert wait_until(lambda: _heatmap_points(client, cid) == 4)

        heat = client.get(f"/api/v1/analytics/campaigns/{cid}/heatmap?cell_size=5").json()
        assert heat["total_points"] == 4
        assert len(heat["cells"]) == 1
        cell = heat["cells"][0]
        assert (cell["x"], cell["y"]) == (10, 15)
        assert cell["movement_count"] == 1
        assert cell["damage_total"] == 40
        assert cell["hit_count"] == 2
        assert cell["knockout_count"] == 1
        # density = movement 1 + damage 30//5 + damage 10//5 + knockout 5
        assert cell["density"] == 14

        coarse = client.get(f"/api/v1/analytics/campaigns/{cid}/heatmap?cell_size=10").json()
        assert (coarse["cells"][0]["x"], coarse["cells"][0]["y"]) == (10, 10)

        movement = client.get(f"/api/v1/analytics/campaigns/{cid}/heatmap?metric=movement").json()
        assert movement["total_points"] == 1
        assert movement["cells"][0]["damage_total"] == 0


def test_mvp_scores_damage_crit_and_healing_per_combatant(
    analytics_service: AnalyticsService,
) -> None:
    """Scores follow the combat formula. Damage and healing go to the active combatant."""
    cid, sid = str(uuid4()), str(uuid4())
    valeros, kyra = str(uuid4()), str(uuid4())
    analytics_service.grant_view(cid)

    with analytics_service.start() as client:
        # A session maps to its campaign on creation. Events without a campaign id rely on it.
        analytics_service.publish(
            SESSION_STREAM,
            SessionCreated(aggregate_id=sid, session_id=sid, campaign_id=cid, title="Lair"),
        )
        analytics_service.publish(
            SESSION_STREAM,
            InitiativeTurnAdvanced(
                aggregate_id=sid,
                session_id=sid,
                campaign_id=cid,
                round_number=1,
                active_combatant_id=valeros,
            ),
        )
        assert wait_until(lambda: _mvp_turns(client, cid, valeros) == 1)

        analytics_service.publish(
            CHARACTER_STREAM,
            CharacterHealthChanged(
                aggregate_id=kyra,
                session_id=sid,
                campaign_id=cid,
                delta=-65,
                current_hp=20,
                max_hp=80,
            ),
        )
        analytics_service.publish(
            WATCHER_STREAM,
            DiceRolled(
                session_id=sid,
                roller_id=valeros,
                roller_name="Valeros",
                formula="1d20+7",
                total=27,
                is_crit=True,
            ),
        )
        assert wait_until(
            lambda: (
                _mvp_damage(client, cid, valeros) == 65
                and _combatant_field(client, cid, valeros, "critical_hits") == 1
            )
        )

        analytics_service.publish(
            SESSION_STREAM,
            InitiativeTurnAdvanced(
                aggregate_id=sid,
                session_id=sid,
                campaign_id=cid,
                round_number=2,
                active_combatant_id=kyra,
            ),
        )
        assert wait_until(lambda: _mvp_turns(client, cid, kyra) == 1)
        analytics_service.publish(
            CHARACTER_STREAM,
            CharacterHealthChanged(
                aggregate_id=valeros,
                session_id=sid,
                campaign_id=cid,
                delta=45,
                current_hp=60,
                max_hp=80,
            ),
        )
        assert wait_until(lambda: _mvp_healing(client, cid, kyra) == 45)

        mvp = _mvp(client, cid)
        # Valeros: 65 damage + 1 crit * 10 + 1 turn * 2 = 77. Kyra: 45 * 1.5 + 1 turn * 2 = 69.5.
        assert mvp["overall_mvp"]["recipient_id"] == valeros
        assert mvp["overall_mvp"]["score"] == 77
        awards = {a["title"]: a for a in mvp["awards"]}
        assert awards["Most Lethal"]["recipient_id"] == valeros
        assert awards["Most Lethal"]["score"] == 65
        assert awards["Guardian Angel"]["recipient_id"] == kyra
        assert awards["Guardian Angel"]["score"] == 45
        assert awards["Nat 20 Master"]["recipient_id"] == valeros


def test_session_resolves_to_campaign_for_events_without_campaign_id(
    analytics_service: AnalyticsService,
) -> None:
    """A roll on a session counts toward the campaign that the session created."""
    cid, sid, roller = str(uuid4()), str(uuid4()), str(uuid4())
    analytics_service.grant_view(cid)

    with analytics_service.start() as client:
        analytics_service.publish(
            SESSION_STREAM,
            SessionCreated(aggregate_id=sid, session_id=sid, campaign_id=cid, title="Crypt"),
        )
        assert wait_until(lambda: _milestone_count(client, cid) == 1)
        analytics_service.publish(
            WATCHER_STREAM,
            DiceRolled(
                session_id=sid,
                roller_id=roller,
                roller_name="Kyra",
                formula="1d20",
                total=20,
                is_crit=True,
            ),
        )
        assert wait_until(lambda: _has_combatant(client, cid, roller))
        mvp = _mvp(client, cid)
        assert [c["combatant_id"] for c in mvp["combatants"]] == [roller]
        assert mvp["combatants"][0]["critical_hits"] == 1


def _mvp_turns(client: Any, cid: str, combatant: str) -> int:
    return _combatant_field(client, cid, combatant, "turns_taken")


def _mvp_damage(client: Any, cid: str, combatant: str) -> int:
    return _combatant_field(client, cid, combatant, "damage_dealt")


def _mvp_healing(client: Any, cid: str, combatant: str) -> int:
    return _combatant_field(client, cid, combatant, "healing_provided")


def _combatant_field(client: Any, cid: str, combatant: str, field: str) -> int:
    for row in _mvp(client, cid).get("combatants", []):
        if row["combatant_id"] == combatant:
            return int(row[field])
    return 0


def _has_combatant(client: Any, cid: str, combatant: str) -> bool:
    return any(row["combatant_id"] == combatant for row in _mvp(client, cid).get("combatants", []))
