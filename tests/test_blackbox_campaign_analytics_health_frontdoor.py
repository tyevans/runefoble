"""Cross-service blackbox test: a health change reaches the campaign MVP route (TASK-0574).

Game session, character sheet, and campaign analytics run as their own FastAPI apps. They
share one Redis transport double, the same one the analytics consumers read. Every step is a
public HTTP route. Nothing writes private aggregate or projection state.

Governed by Hard Invariant 7 and ADR-0015 (each service verifies its own token).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from character_sheet import dependencies as sheet_deps
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient
from game_session import dependencies as session_deps
from game_session.main import app as game_app
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.campaign_analytics_service import AnalyticsService, wait_until
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def shared_transport(analytics_service: AnalyticsService) -> Iterator[None]:
    """Route game session and character sheet publishes to the analytics transport."""
    bus = RedisStreamsEventBus(client=analytics_service.redis)
    previous_session = session_deps.get_event_bus()
    previous_sheet = sheet_deps.get_event_bus()
    session_deps.set_event_bus(bus)
    sheet_deps.set_event_bus(bus)
    try:
        yield
    finally:
        session_deps.set_event_bus(previous_session)
        sheet_deps.set_event_bus(previous_sheet)


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}


def _damage_taken(analytics: TestClient, campaign_id: str, combatant_id: str) -> int:
    rows = analytics.get(f"/api/v1/analytics/campaigns/{campaign_id}/mvp").json()["combatants"]
    return sum(int(r["damage_taken"]) for r in rows if r["combatant_id"] == combatant_id)


def test_health_change_in_combat_reaches_campaign_mvp_through_public_routes(
    analytics_service: AnalyticsService, shared_transport: None
) -> None:
    """Combat and damage set up through game session and character sheet appear in the MVP."""
    with analytics_service.start() as analytics:
        game = TestClient(game_app, headers=_headers())
        sheet = TestClient(character_app, headers=_headers())

        campaign_id = game.post("/api/v1/campaigns", json={"title": "Frontdoor"})
        assert campaign_id.status_code == 201, campaign_id.text
        campaign_id = campaign_id.json()["id"]
        analytics_service.grant_view(campaign_id)

        created = sheet.post(
            "/api/v1/characters",
            json={
                "name": "Valeros",
                "character_class": "Fighter",
                "max_hp": 30,
                "campaign_id": campaign_id,
            },
        )
        assert created.status_code == 200, created.text
        char_id = created.json()["character_id"]

        session_id = game.post(
            "/api/v1/sessions/create",
            json={"campaign_id": campaign_id, "title": "Ambush", "dm_id": "the_watcher"},
        ).json()["session_id"]
        joined = game.post(
            f"/api/v1/sessions/{session_id}/join",
            json={
                "player_id": "player-1",
                "character_id": char_id,
                "character_name": "Valeros",
                "character_class": "Fighter",
            },
        )
        assert joined.status_code == 200, joined.text
        assert game.post(f"/api/v1/sessions/{session_id}/start").status_code == 200
        assert game.post(f"/api/v1/sessions/{session_id}/combat/start").status_code == 200
        rolled = game.post(
            f"/api/v1/sessions/{session_id}/combat/initiative",
            json={
                "combatant_id": char_id,
                "combatant_name": "Valeros",
                "initiative_score": 18,
            },
        )
        assert rolled.status_code == 200, rolled.text
        turn = game.post(
            f"/api/v1/sessions/{session_id}/combat/next-turn", json={"turn_seconds": 45}
        )
        assert turn.status_code == 200, turn.text
        assert turn.json()["combat_active_id"] == char_id

        hit = sheet.post(
            f"/api/v1/characters/{char_id}/health",
            json={"delta": -7, "source": "Goblin Arrow", "session_id": session_id},
        )
        assert hit.status_code == 200, hit.text

        assert wait_until(lambda: _damage_taken(analytics, campaign_id, char_id) == 7)
