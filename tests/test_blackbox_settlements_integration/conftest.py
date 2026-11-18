"""Shared fixtures and stream utilities for settlement blackbox integration tests."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as session_app
from game_session.settlement import auth as settlement_auth
from gateway_api.auth import set_zitadel_auth_service as set_gw_verifier
from gateway_api.main import app as gateway_app
from gateway_api.websocket_manager import ws_campaign_manager
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER


@pytest.fixture
def settlement_issuer() -> Generator[SigningTestIssuer]:
    """Trust one signing issuer in the game_session and gateway verifiers for one test."""
    issuer = SigningTestIssuer()
    verifier = issuer.verifier()
    settlement_auth.set_zitadel_auth_service(verifier)
    set_gw_verifier(verifier)
    yield issuer
    settlement_auth.set_zitadel_auth_service(None)
    set_gw_verifier(None)


def bearer_headers(issuer: SigningTestIssuer, sub: str) -> dict[str, str]:
    """Return Authorization headers carrying a token that the verifiers accept for `sub`."""
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


def ws_subprotocols(headers: dict[str, str]) -> list[str]:
    """Return the WebSocket subprotocols that carry the bearer token from `headers`."""
    token = headers["Authorization"].removeprefix("Bearer ")
    return ["runefoble.v1", f"runefoble.bearer.{token}"]


@pytest.fixture
def session_client(
    spicedb: MockSpiceDBClient,
    mock_bus: MockAsyncRedis,
    trusted_ws_issuer: SigningTestIssuer,
) -> TestClient:
    return TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )


client = session_client


@pytest.fixture
def gateway_client(
    spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis, settlement_issuer: SigningTestIssuer
) -> TestClient:
    return TestClient(gateway_app)


@pytest.fixture(autouse=True)
def clean_gateway_ws() -> Generator[None]:
    ws_campaign_manager.active_connections.clear()
    yield
    ws_campaign_manager.active_connections.clear()


def setup_campaign_settlement(
    tc: TestClient,
    db: MockSpiceDBClient,
    dist: list[str] | None = None,
    issuer: SigningTestIssuer | None = None,
) -> tuple[str, str, str, dict[str, str], dict[str, str]]:
    """Create a campaign and a haven. Pass `issuer` to send signed bearer tokens instead."""
    cid, dm_id, p_id = str(uuid4()), f"dm_{uuid4().hex[:6]}", f"p_{uuid4().hex[:6]}"
    for r, u in [("player", p_id), ("player", dm_id), ("dungeon_master", dm_id)]:
        asyncio.run(db.write_relationship("campaign", cid, r, "user", u))
    if issuer is None:
        h, p_h = (
            {"Authorization": f"Bearer {SIGNING_ISSUER.mint(dm_id)}"},
            {"Authorization": f"Bearer {SIGNING_ISSUER.mint(p_id)}"},
        )
    else:
        h, p_h = bearer_headers(issuer, dm_id), bearer_headers(issuer, p_id)
    b = {"name": "Haven", "scale": "village", **({"districts": dist} if dist else {})}
    sid = tc.post(f"/api/v1/campaigns/{cid}/settlements", json=b, headers=h).json()["settlement_id"]
    return cid, sid, p_id, h, p_h
