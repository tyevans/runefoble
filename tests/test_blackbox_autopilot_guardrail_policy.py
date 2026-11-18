"""Blackbox tests for the stored stand-in policy on the auto-pilot route (TASK-0691, TASK-0779).

Auto-pilot reads the policy stored on the absent character through character_sheet. The request
carries no policy: a body with a `guardrails` field answers 422 and records no action. A character
with no stored policy uses the shared default policy. An unavailable character_sheet stops the
turn with 503.
"""

from __future__ import annotations

import socket
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from game_session.character_client import CHARACTER_SHEET_URL_ENV
from game_session.main import app as session_app
from httpx import ASGITransport, AsyncClient

from tests.helpers.stand_in_policy import create_character, store_policy
from tests.helpers.watcher_double import STAND_IN_ACTION_BODY, serve_watcher_double
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

AUTO_PILOT_PATH = "/api/v1/sessions/{session_id}/turns/auto-pilot"
OWNER = "test-user"
SHARED_DEFAULT_POLICY: dict[str, Any] = {
    "preserve_spell_slots": {},
    "protect_allies": [],
    "protect_ally_hp_threshold": 0.3,
    "risk_threshold": "cautious",
    "avoid_melee": True,
    "permadeath_safeguard": True,
    "custom_priorities": [],
}


@pytest.fixture
def client() -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=session_app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(OWNER)}"},
    )


def _capturing_watcher(received: list[dict[str, Any]]) -> FastAPI:
    """A Watcher double that records each stand-in request body and answers with a fixed action."""
    app = FastAPI()

    @app.post("/api/v1/watcher/stand-in/act")
    async def stand_in_act(request: Request) -> JSONResponse:
        received.append(await request.json())
        return JSONResponse(content=STAND_IN_ACTION_BODY)

    return app


async def _owned_campaign(client: AsyncClient) -> str:
    res = await client.post("/api/v1/campaigns", json={"title": "Policy Campaign"})
    assert res.status_code == 201, res.text
    return res.json()["id"]


async def _start_session_with_absent_player(client: AsyncClient, character_id: str) -> str:
    """Create, join, start, and leave a session through public routes. Return its id."""
    create_res = await client.post(
        "/api/v1/sessions/create",
        json={
            "campaign_id": await _owned_campaign(client),
            "title": "Policy Session",
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
        f"/api/v1/sessions/{session_id}/leave", json={"reason": "Sick with flu"}
    )
    assert leave_res.status_code == 200
    return session_id


@pytest.fixture
def unreachable_watcher(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Point the session at a closed port. A request that reaches The Watcher fails with 503."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        closed_port = probe.getsockname()[1]
    monkeypatch.setenv("RUNEFOBLE_WATCHER_URL", f"http://127.0.0.1:{closed_port}")
    yield


@pytest.mark.asyncio
async def test_auto_pilot_rejects_a_policy_in_the_request_body_with_422(
    client: AsyncClient, unreachable_watcher: None
) -> None:
    """The policy is not a request field. The Watcher is never reached and no action is recorded."""
    async with client:
        session_id = await _start_session_with_absent_player(client, str(uuid4()))

        res = await client.post(
            AUTO_PILOT_PATH.format(session_id=session_id),
            json={"guardrails": {"protect_allies": ["Marcus"]}},
        )

        assert res.status_code == 422
        assert "guardrails" in res.text
        state = (await client.get(f"/api/v1/sessions/{session_id}")).json()
        assert state["current_turn"] == 1
        assert state["stand_in_actions"] == []


@pytest.mark.asyncio
async def test_auto_pilot_forwards_the_stored_policy_to_the_watcher(
    client: AsyncClient, live_character_sheet: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    character_id = create_character(live_character_sheet, OWNER)
    store_policy(
        live_character_sheet,
        OWNER,
        character_id,
        {
            "preserve_spell_slots": {"3": 1},
            "protect_allies": ["Marcus"],
            "avoid_melee": False,
        },
    )
    received: list[dict[str, Any]] = []
    with serve_watcher_double(_capturing_watcher(received)) as watcher_url:
        monkeypatch.setenv("RUNEFOBLE_WATCHER_URL", watcher_url)
        async with client:
            session_id = await _start_session_with_absent_player(client, character_id)

            res = await client.post(AUTO_PILOT_PATH.format(session_id=session_id))

    assert res.status_code == 200, res.text
    assert len(received) == 1
    assert received[0]["guardrails"] == {
        **SHARED_DEFAULT_POLICY,
        "preserve_spell_slots": {"3": 1},
        "protect_allies": ["Marcus"],
        "avoid_melee": False,
    }


@pytest.mark.asyncio
async def test_auto_pilot_without_a_stored_policy_forwards_the_shared_default(
    client: AsyncClient, live_character_sheet: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    character_id = create_character(live_character_sheet, OWNER, "Brynn")
    received: list[dict[str, Any]] = []
    with serve_watcher_double(_capturing_watcher(received)) as watcher_url:
        monkeypatch.setenv("RUNEFOBLE_WATCHER_URL", watcher_url)
        async with client:
            session_id = await _start_session_with_absent_player(client, character_id)

            res = await client.post(AUTO_PILOT_PATH.format(session_id=session_id))

    assert res.status_code == 200, res.text
    assert received[0]["guardrails"] == SHARED_DEFAULT_POLICY


@pytest.mark.asyncio
async def test_auto_pilot_refuses_when_the_stored_policy_is_unavailable(
    client: AsyncClient,
    live_character_sheet: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """character_sheet is down when the turn runs. The turn stops. No default policy is used."""
    character_id = create_character(live_character_sheet, OWNER)
    received: list[dict[str, Any]] = []
    with serve_watcher_double(_capturing_watcher(received)) as watcher_url:
        monkeypatch.setenv("RUNEFOBLE_WATCHER_URL", watcher_url)
        async with client:
            session_id = await _start_session_with_absent_player(client, character_id)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind(("127.0.0.1", 0))
                closed_port = probe.getsockname()[1]
            monkeypatch.setenv(CHARACTER_SHEET_URL_ENV, f"http://127.0.0.1:{closed_port}")

            res = await client.post(AUTO_PILOT_PATH.format(session_id=session_id))

            assert res.status_code == 503
            assert "stored stand-in policy" in res.json()["detail"]
            state = (await client.get(f"/api/v1/sessions/{session_id}")).json()
            assert state["current_turn"] == 1
            assert state["stand_in_actions"] == []
    assert received == []
