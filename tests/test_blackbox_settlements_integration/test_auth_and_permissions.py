"""Authentication, Zitadel token extraction, route dependencies, and settlement auth lifecycle."""

from __future__ import annotations

import asyncio
from typing import Annotated

import pytest
from fastapi import APIRouter, Depends, HTTPException
from fastapi.testclient import TestClient
from game_session.main import app as session_app
from game_session.settlement import auth as sa
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_auth.zitadel import ZitadelAuthService

from tests.helpers.ws_identity import SIGNING_ISSUER

from .conftest import bearer_headers

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


def test_bearer_token_extraction_and_decoding():
    """Verify bearer token extraction and that a missing token is refused without fallback."""
    assert sa.extract_bearer_token(None) is None
    assert sa.extract_bearer_token("Basic 12345") is None
    assert sa.extract_bearer_token("Bearer secret_jwt_token") == "secret_jwt_token"

    service = ZitadelAuthService(
        issuer="http://zitadel.test", audience="runefoble-api", internal_url=None
    )
    sa.set_zitadel_auth_service(service)
    try:
        with pytest.raises(HTTPException) as exc:
            sa.decode_settlement_token(authorization=None)
        assert exc.value.status_code == 401
    finally:
        sa.set_zitadel_auth_service(None)


def test_fastapi_route_dependencies(spicedb: MockSpiceDBClient, settlement_issuer):
    """Verify FastAPI dependency factories enforce Zanzibar object-level permissions."""
    r = APIRouter(prefix="/api/v1/test_auth")

    @r.get("/h/{s}", dependencies=[Depends(sa.require_haven_builder("s"))])
    async def h_ep(u: Annotated[sa.VerifiedPrincipal, Depends(sa.get_current_settlement_user)]):
        return {"user": u.user_id}

    @r.get("/e/{e}", dependencies=[Depends(sa.require_establishment_manager("e"))])
    async def e_ep(u: Annotated[sa.VerifiedPrincipal, Depends(sa.get_current_settlement_user)]):
        return {"user": u.user_id}

    session_app.include_router(r)
    tc = TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )
    asyncio.run(spicedb.write_relationship("settlement", "h1", "founder", "user", "builder"))
    asyncio.run(spicedb.write_relationship("establishment", "e1", "manager", "user", "builder"))

    builder = bearer_headers(settlement_issuer, "builder")
    intruder = bearer_headers(settlement_issuer, "intruder")
    assert tc.get("/api/v1/test_auth/h/h1", headers=builder).status_code == 200
    assert tc.get("/api/v1/test_auth/e/e1", headers=builder).status_code == 200
    assert tc.get("/api/v1/test_auth/h/h1", headers=intruder).status_code == 403
    assert tc.get("/api/v1/test_auth/e/e1", headers=intruder).status_code == 403
    assert tc.get("/api/v1/test_auth/h/h1").status_code == 401


def test_frontdoor_settlement_auth_lifecycle(session_client: TestClient):
    """End-to-end blackbox frontdoor verifying authorization across settlement and establishment endpoints."""
    gm_id, p_id, int_id = "gm_1", "p_1", "int_1"
    gm_h = {"Authorization": f"Bearer {SIGNING_ISSUER.mint(gm_id)}"}
    p_h = {"Authorization": f"Bearer {SIGNING_ISSUER.mint(p_id)}"}
    created = session_client.post(
        "/api/v1/campaigns", json={"title": "Frontier Watch"}, headers=gm_h
    )
    assert created.status_code == 201
    cid = created.json()["id"]
    invite = session_client.post(
        f"/api/v1/campaigns/{cid}/invites", json={"role": "player"}, headers=gm_h
    )
    assert invite.status_code == 201
    joined = session_client.post(
        "/api/v1/campaigns/join", json={"invite_token": invite.json()["token"]}, headers=p_h
    )
    assert joined.status_code == 200

    url = f"/api/v1/campaigns/{cid}/settlements"
    bad = session_client.post(
        url,
        json={"name": "Outlaw Camp", "scale": "hamlet"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(int_id)}"},
    )
    assert bad.status_code == 403

    ok = session_client.post(
        url,
        json={"name": "Garrison Prime", "scale": "village"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(gm_id)}"},
    )
    assert ok.status_code == 201
    sid = ok.json()["settlement_id"]

    assert (
        session_client.get(
            f"{url}/{sid}", headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(p_id)}"}
        ).status_code
        == 200
    )
    assert (
        session_client.get(
            f"{url}/{sid}", headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(int_id)}"}
        ).status_code
        == 403
    )
