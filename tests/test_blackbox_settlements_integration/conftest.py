"""Shared fixtures and stream utilities for settlement blackbox integration tests."""

from __future__ import annotations

from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as session_app
from game_session.settlement import auth as settlement_auth
from gateway_api.auth import get_zitadel_auth_service as get_gw_verifier
from gateway_api.auth import set_zitadel_auth_service as set_gw_verifier
from gateway_api.main import app as gateway_app
from gateway_api.websocket_manager import ws_campaign_manager
from runefoble_auth.mock import MockSpiceDBClient
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer

from tests.helpers.campaign_setup import create_campaign, invite_and_join
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.module_state import SeamRestorer
from tests.helpers.ws_identity import SIGNING_ISSUER


@pytest.fixture
def settlement_issuer(seam_restorer: SeamRestorer) -> Generator[SigningTestIssuer]:
    """Trust one signing issuer in the game_session and gateway verifiers for one test."""
    issuer = SigningTestIssuer()
    verifier = issuer.verifier()
    seam_restorer.replace(
        settlement_auth.get_zitadel_auth_service, settlement_auth.set_zitadel_auth_service, verifier
    )
    seam_restorer.replace(get_gw_verifier, set_gw_verifier, verifier)
    yield issuer


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
    ws_campaign_manager.clear()
    yield
    ws_campaign_manager.clear()


def setup_campaign_settlement(
    tc: TestClient,
    dist: list[str] | None = None,
    issuer: SigningTestIssuer | None = None,
) -> tuple[str, str, str, dict[str, str], dict[str, str]]:
    """Create a campaign with an owner and a player, then found a haven.

    The owner creates the campaign and the player joins through the invite and join routes.
    Pass `issuer` to send signed bearer tokens from that issuer instead.
    """
    signer = issuer or SIGNING_ISSUER
    dm_id, p_id = f"dm_{uuid4().hex[:6]}", f"p_{uuid4().hex[:6]}"
    cid = create_campaign(tc, dm_id, issuer=signer)
    invite_and_join(tc, cid, dm_id, p_id, "player", issuer=signer)
    h, p_h = bearer_headers(signer, dm_id), bearer_headers(signer, p_id)
    b = {"name": "Haven", "scale": "village", **({"districts": dist} if dist else {})}
    sid = tc.post(f"/api/v1/campaigns/{cid}/settlements", json=b, headers=h).json()["settlement_id"]
    return cid, sid, p_id, h, p_h
