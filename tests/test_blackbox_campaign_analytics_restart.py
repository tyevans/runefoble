"""Blackbox tests: Campaign Analytics read models survive a restart on the same PostgreSQL.

Governed by ADR-0011, ADR-0015 (fail-closed start-up), and Hard Invariant 7. Events enter
through the Redis Streams transport. Results are read through public HTTP routes. Each restart
is a new lifespan on the same database, so the projection state comes from PostgreSQL only.
"""

from __future__ import annotations

import socket
from typing import Any
from uuid import uuid4

import pytest
import redis.asyncio
from runefoble_events.events import (
    CharacterHealthChanged,
    CombatEncounterStarted,
    InitiativeTurnAdvanced,
    SessionCreated,
)
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import set_event_store

from tests.helpers.campaign_analytics_service import (
    CHARACTER_STREAM,
    SESSION_STREAM,
    AnalyticsService,
    wait_until,
)
from tests.helpers.mock_redis import MockAsyncRedis


def _hp(char_id: str, sid: str, cid: str, delta: int, current_hp: int) -> Any:
    """Damage taken by a character. The damage is credited to the session's active combatant."""
    return CharacterHealthChanged(
        aggregate_id=char_id,
        session_id=sid,
        campaign_id=cid,
        delta=delta,
        current_hp=current_hp,
        max_hp=60,
        source="test",
    )


def _mvp_damage(client: Any, cid: str, sid: str, recipient: str) -> int:
    body = client.get(f"/api/v1/analytics/campaigns/{cid}/mvp?session_id={sid}").json()
    row = next((c for c in body["combatants"] if c["combatant_id"] == recipient), None)
    return 0 if row is None else row["damage_dealt"]


def _timeline_types(client: Any, cid: str) -> list[str]:
    body = client.get(f"/api/v1/analytics/campaigns/{cid}/timeline?limit=500").json()
    return [m["type"] for m in body["milestones"]]


def test_mvp_and_timeline_survive_restart_without_double_counting(
    analytics_service: AnalyticsService,
) -> None:
    """Stats and milestones written before a restart are still served after it, once each."""
    cid, sid = str(uuid4()), str(uuid4())
    valeros, kyra = str(uuid4()), str(uuid4())
    analytics_service.grant_view(cid)

    with analytics_service.start() as first:
        analytics_service.publish(
            SESSION_STREAM,
            SessionCreated(aggregate_id=sid, session_id=sid, campaign_id=cid, title="Lair"),
        )
        analytics_service.publish(
            SESSION_STREAM,
            CombatEncounterStarted(
                aggregate_id=sid, session_id=sid, campaign_id=cid, round_number=1, combatants=[]
            ),
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
        # Session and character streams are consumed by separate loops. Wait for the round, so
        # the damage is credited to the active combatant.
        assert wait_until(lambda: "combat_round" in _timeline_types(first, cid))
        analytics_service.publish(CHARACTER_STREAM, _hp(kyra, sid, cid, -40, 20))

        assert wait_until(lambda: _mvp_damage(first, cid, sid, valeros) == 40)
        types_before = sorted(_timeline_types(first, cid))
        assert "boss_encounter" in types_before
        assert "combat_round" in types_before

    # The service is down. Redis loses its consumer group state, so a new group starts at "0".
    # Only the position stored with the read model can stop a full replay from double counting.
    analytics_service.redis.groups.clear()
    analytics_service.publish(CHARACTER_STREAM, _hp(kyra, sid, cid, -10, 10))

    with analytics_service.start() as second:
        assert wait_until(lambda: _mvp_damage(second, cid, sid, valeros) == 50)
        # Replay from the start would count the first 40 damage again. Wait, then confirm.
        assert _mvp_damage(second, cid, sid, valeros) == 50
        assert sorted(_timeline_types(second, cid)) == types_before


def test_start_up_fails_when_database_is_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    """The service does not start without its PostgreSQL store. It serves no empty projection."""
    import campaign_analytics.main as analytics_main
    from fastapi.testclient import TestClient

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        closed_port = probe.getsockname()[1]

    monkeypatch.setenv(
        "RUNEFOBLE_DATABASE_URL",
        f"postgresql+asyncpg://u:p@127.0.0.1:{closed_port}/analytics",
    )
    monkeypatch.setattr(analytics_main, "platform_settings", PlatformSettings())
    double = MockAsyncRedis()
    monkeypatch.setattr(redis.asyncio, "from_url", lambda *_a, **_k: double)
    set_event_store(None)
    try:
        with pytest.raises(OSError), TestClient(analytics_main.app):
            pass
    finally:
        set_event_store(None)


def test_start_up_fails_when_database_url_is_not_postgresql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SQLite is not a supported store. The service refuses to start on it."""
    import campaign_analytics.main as analytics_main
    from campaign_analytics.storage import StorageConfigurationError
    from fastapi.testclient import TestClient

    monkeypatch.setenv("RUNEFOBLE_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setattr(analytics_main, "platform_settings", PlatformSettings())
    monkeypatch.setattr(redis.asyncio, "from_url", lambda *_a, **_k: MockAsyncRedis())
    set_event_store(None)
    try:
        with pytest.raises(StorageConfigurationError), TestClient(analytics_main.app):
            pass
    finally:
        set_event_store(None)
