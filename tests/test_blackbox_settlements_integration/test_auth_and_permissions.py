"""Authentication, Zitadel token extraction, route dependencies, and settlement auth lifecycle."""

from __future__ import annotations

import asyncio
from typing import Annotated
from uuid import uuid4

import pytest
from fastapi import APIRouter, Depends, HTTPException
from fastapi.testclient import TestClient
from game_session.main import app as session_app
from game_session.settlement import auth as sa
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_auth.zitadel import ZitadelAuthService

from .conftest import bearer_headers


def test_bearer_token_extraction_and_decoding():
    """Verify bearer token extraction and that a missing token is refused without fallback."""
    assert sa.extract_bearer_token(None) is None
    assert sa.extract_bearer_token("Basic 12345") is None
    assert sa.extract_bearer_token("Bearer secret_jwt_token") == "secret_jwt_token"

    service = ZitadelAuthService()
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
    tc = TestClient(session_app)
    asyncio.run(spicedb.write_relationship("settlement", "h1", "upgrade", "user", "builder"))
    asyncio.run(spicedb.write_relationship("establishment", "e1", "manage", "user", "builder"))

    builder = bearer_headers(settlement_issuer, "builder")
    intruder = bearer_headers(settlement_issuer, "intruder")
    assert tc.get("/api/v1/test_auth/h/h1", headers=builder).status_code == 200
    assert tc.get("/api/v1/test_auth/e/e1", headers=builder).status_code == 200
    assert tc.get("/api/v1/test_auth/h/h1", headers=intruder).status_code == 403
    assert tc.get("/api/v1/test_auth/e/e1", headers=intruder).status_code == 403
    assert tc.get("/api/v1/test_auth/h/h1").status_code == 401


def test_frontdoor_settlement_auth_lifecycle(
    session_client: TestClient, spicedb: MockSpiceDBClient
):
    """End-to-end blackbox frontdoor verifying authorization across settlement and establishment endpoints."""
    cid, gm_id, p_id, int_id = str(uuid4()), "gm_1", "p_1", "int_1"
    asyncio.run(spicedb.write_relationship("campaign", cid, "manage", "user", gm_id))
    asyncio.run(spicedb.write_relationship("campaign", cid, "play", "user", p_id))

    url = f"/api/v1/campaigns/{cid}/settlements"
    bad = session_client.post(
        url, json={"name": "Outlaw Camp", "scale": "hamlet"}, headers={"x-user-id": int_id}
    )
    assert bad.status_code == 403

    ok = session_client.post(
        url, json={"name": "Garrison Prime", "scale": "village"}, headers={"x-user-id": gm_id}
    )
    assert ok.status_code == 201
    sid = ok.json()["settlement_id"]

    assert session_client.get(f"{url}/{sid}", headers={"x-user-id": p_id}).status_code == 200
    assert session_client.get(f"{url}/{sid}", headers={"x-user-id": int_id}).status_code == 403
