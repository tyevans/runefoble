"""Blackbox checks for auto-pilot when The Watcher is not configured or fails (ADR-0015 4).

Auto-pilot never runs a local engine in place of The Watcher. When The Watcher is
missing, unreachable, or returns an error, the route returns 503 and records no action.
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from game_session.main import app as session_app
from httpx import ASGITransport, AsyncClient

from tests.helpers.ports import free_port
from tests.helpers.stand_in_policy import create_character
from tests.helpers.watcher_double import serve_watcher_double, watcher_stand_in_app
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")
OWNER = "test-user"

AUTO_PILOT_PATH = "/api/v1/sessions/{session_id}/turns/auto-pilot"


@pytest.fixture
def session_bus() -> Iterator[None]:
    yield


@pytest.fixture
def client() -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=session_app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"},
    )


async def _start_session_with_absent_player(client: AsyncClient, character_id: str) -> str:
    """Create, join, start, and leave a session through public routes. Return its id."""
    create_res = await client.post(
        "/api/v1/sessions/create",
        json={
            "campaign_id": await _owned_campaign(client),
            "title": "Absent Session",
            "dm_id": "dm_alice",
        },
    )
    assert create_res.status_code == 200
    session_id = create_res.json()["session_id"]
    join_res = await client.post(
        f"/api/v1/sessions/{session_id}/join",
        json={
            "character_id": character_id,
            "character_name": "Kyra",
            "character_class": "Cleric",
        },
    )
    assert join_res.status_code == 200
    assert (await client.post(f"/api/v1/sessions/{session_id}/start")).status_code == 200
    leave_res = await client.post(
        f"/api/v1/sessions/{session_id}/leave",
        json={"reason": "Sick with flu"},
    )
    assert leave_res.status_code == 200
    return session_id


async def _assert_no_action_recorded(client: AsyncClient, session_id: str) -> None:
    state = (await client.get(f"/api/v1/sessions/{session_id}")).json()
    assert state["current_turn"] == 1
    assert state["stand_in_actions"] == []


@pytest.mark.asyncio
async def test_auto_pilot_returns_503_when_watcher_url_is_unset(
    client: AsyncClient, session_bus: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("RUNEFOBLE_WATCHER_URL", raising=False)
    async with client:
        session_id = await _start_session_with_absent_player(client, str(uuid4()))

        res = await client.post(AUTO_PILOT_PATH.format(session_id=session_id), json={})

        assert res.status_code == 503
        assert "RUNEFOBLE_WATCHER_URL" in res.json()["detail"]
        await _assert_no_action_recorded(client, session_id)


@pytest.mark.asyncio
async def test_auto_pilot_returns_503_when_watcher_returns_an_error(
    client: AsyncClient,
    session_bus: None,
    live_character_sheet: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = watcher_stand_in_app(status_code=503, body={"detail": "inference worker down"})
    with serve_watcher_double(app) as watcher_url:
        monkeypatch.setenv("RUNEFOBLE_WATCHER_URL", watcher_url)
        async with client:
            session_id = await _start_session_with_absent_player(
                client, create_character(live_character_sheet, OWNER)
            )

            res = await client.post(AUTO_PILOT_PATH.format(session_id=session_id), json={})

            assert res.status_code == 503
            assert "HTTP 503" in res.json()["detail"]
            await _assert_no_action_recorded(client, session_id)


@pytest.mark.asyncio
async def test_auto_pilot_returns_503_when_watcher_is_unreachable(
    client: AsyncClient,
    session_bus: None,
    live_character_sheet: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed_port = free_port()
    monkeypatch.setenv("RUNEFOBLE_WATCHER_URL", f"http://127.0.0.1:{closed_port}")
    async with client:
        session_id = await _start_session_with_absent_player(
            client, create_character(live_character_sheet, OWNER)
        )

        res = await client.post(AUTO_PILOT_PATH.format(session_id=session_id), json={})

        assert res.status_code == 503
        await _assert_no_action_recorded(client, session_id)


@pytest.mark.asyncio
async def test_auto_pilot_records_the_action_from_the_configured_watcher(
    client: AsyncClient,
    session_bus: None,
    live_character_sheet: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with serve_watcher_double(watcher_stand_in_app()) as watcher_url:
        monkeypatch.setenv("RUNEFOBLE_WATCHER_URL", watcher_url)
        async with client:
            session_id = await _start_session_with_absent_player(
                client, create_character(live_character_sheet, OWNER)
            )

            res = await client.post(
                AUTO_PILOT_PATH.format(session_id=session_id),
                json={"penalties": ["drunk"]},
            )

            assert res.status_code == 200
            assert res.json()["action"]["dialogue"] == "Configured Watcher says hello."
            state = (await client.get(f"/api/v1/sessions/{session_id}")).json()
            assert state["current_turn"] == 2
            assert state["stand_in_actions"][0]["dialogue"] == "Configured Watcher says hello."


async def _owned_campaign(client) -> str:
    """Create a campaign as the calling user, so that the caller can run sessions in it."""
    res = await client.post("/api/v1/campaigns", json={"title": "Owned Campaign"})
    assert res.status_code == 201, res.text
    return res.json()["id"]
