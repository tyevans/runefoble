"""Blackbox tests: the gateway survives stale pooled connections to an owner (TASK-0936).

After an owner restart, the gateway pool can hold keep-alive connections that close before
any answer. A GET through the gateway is sent again once and succeeds. A POST answers 503,
because the owner may have applied it. The owner runs as a raw loopback server that drops
the second request on each connection. Requests go through the gateway public routes.

Governed by:
- TASK-0936: The Service Client Recovers From Stale Pooled Connections
- ADR-0015: an outage is reported, never hidden
- Hard Invariant 7: Blackbox TDD with public frontdoors
"""

from __future__ import annotations

import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.live_services import unanswered_port_url
from tests.helpers.stale_connection_owner import stale_connection_owner
from tests.helpers.ws_identity import bearer

OFFICER = "guild_officer_marrow"
UNAVAILABLE = {"detail": "Upstream service is unavailable", "upstream": "game_session"}


def _contracts_url(world_id: str) -> str:
    return f"/api/v1/shared-worlds/{world_id}/caravans/contracts"


def test_second_get_on_a_stale_owner_connection_succeeds(
    trusted_ws_issuer, monkeypatch: pytest.MonkeyPatch
) -> None:
    world_id = str(uuid4())
    with stale_connection_owner() as owner:
        monkeypatch.setenv("RUNEFOBLE_GAME_SESSION_URL", owner.base_url)
        with TestClient(gateway_app) as client:
            first = client.get(_contracts_url(world_id), headers=bearer(OFFICER))
            second = client.get(_contracts_url(world_id), headers=bearer(OFFICER))

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert len(owner.dropped) == 1


def test_second_post_on_a_stale_owner_connection_answers_503(
    trusted_ws_issuer, monkeypatch: pytest.MonkeyPatch
) -> None:
    fulfil = f"{_contracts_url(str(uuid4()))}/{uuid4()}/fulfill"
    with stale_connection_owner() as owner:
        monkeypatch.setenv("RUNEFOBLE_GAME_SESSION_URL", owner.base_url)
        with TestClient(gateway_app) as client:
            first = client.post(fulfil, json={}, headers=bearer(OFFICER))
            second = client.post(fulfil, json={}, headers=bearer(OFFICER))

    assert first.status_code == 200, first.text
    assert second.status_code == 503
    assert second.json() == UNAVAILABLE
    assert len(owner.received) == 2


def test_get_to_a_down_owner_still_answers_503_within_the_connect_limit(
    trusted_ws_issuer, monkeypatch: pytest.MonkeyPatch
) -> None:
    with unanswered_port_url() as owner_url:
        monkeypatch.setenv("RUNEFOBLE_GAME_SESSION_URL", owner_url)
        with TestClient(gateway_app) as client:
            started = time.monotonic()
            res = client.get(_contracts_url(str(uuid4())), headers=bearer(OFFICER))
            elapsed = time.monotonic() - started

    assert res.status_code == 503
    assert res.json() == UNAVAILABLE
    assert elapsed < 3.0
