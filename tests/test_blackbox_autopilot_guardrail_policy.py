"""Blackbox tests for the typed stand-in policy on the auto-pilot route (TASK-0691).

The policy travels in the auto-pilot request. game_session validates it with the shared
StandInGuardrailPolicy model before any Watcher call. A rejected policy returns 422 with the
field name and records no action. A valid policy reaches The Watcher unchanged.
"""

from __future__ import annotations

import socket
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from game_session.main import app as session_app
from httpx import ASGITransport, AsyncClient

from tests.helpers.watcher_double import STAND_IN_ACTION_BODY, serve_watcher_double
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

AUTO_PILOT_PATH = "/api/v1/sessions/{session_id}/turns/auto-pilot"


@pytest.fixture
def client() -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=session_app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"},
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


async def _start_session_with_absent_player(client: AsyncClient) -> str:
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
            "character_id": str(uuid4()),
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
async def test_auto_pilot_rejects_an_unknown_guardrail_name_with_422(
    client: AsyncClient, unreachable_watcher: None
) -> None:
    """An unknown guardrail name is refused at the boundary. The Watcher is never reached."""
    async with client:
        session_id = await _start_session_with_absent_player(client)

        res = await client.post(
            AUTO_PILOT_PATH.format(session_id=session_id),
            json={"guardrails": {"protect_allys": ["Marcus"]}},
        )

        assert res.status_code == 422
        assert "protect_allys" in res.text
        state = (await client.get(f"/api/v1/sessions/{session_id}")).json()
        assert state["current_turn"] == 1
        assert state["stand_in_actions"] == []


@pytest.mark.asyncio
async def test_auto_pilot_rejects_a_wrongly_typed_guardrail_with_422(
    client: AsyncClient, unreachable_watcher: None
) -> None:
    async with client:
        session_id = await _start_session_with_absent_player(client)

        res = await client.post(
            AUTO_PILOT_PATH.format(session_id=session_id),
            json={"guardrails": {"risk_threshold": "fearless"}},
        )

        assert res.status_code == 422
        assert "risk_threshold" in res.text


@pytest.mark.asyncio
async def test_auto_pilot_forwards_the_typed_policy_to_the_watcher(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    received: list[dict[str, Any]] = []
    with serve_watcher_double(_capturing_watcher(received)) as watcher_url:
        monkeypatch.setenv("RUNEFOBLE_WATCHER_URL", watcher_url)
        async with client:
            session_id = await _start_session_with_absent_player(client)

            res = await client.post(
                AUTO_PILOT_PATH.format(session_id=session_id),
                json={
                    "guardrails": {
                        "preserve_spell_slots": {"3": 1},
                        "protect_allies": ["Marcus"],
                    }
                },
            )

    assert res.status_code == 200
    assert len(received) == 1
    forwarded = received[0]["guardrails"]
    assert forwarded["preserve_spell_slots"] == {"3": 1}
    assert forwarded["protect_allies"] == ["Marcus"]
    assert forwarded["risk_threshold"] == "cautious"
    assert set(forwarded) == {
        "preserve_spell_slots",
        "protect_allies",
        "protect_ally_hp_threshold",
        "risk_threshold",
        "avoid_melee",
        "permadeath_safeguard",
        "custom_priorities",
    }
