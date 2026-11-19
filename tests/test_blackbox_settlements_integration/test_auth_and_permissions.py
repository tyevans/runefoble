"""Authentication, Zitadel token extraction, route dependencies, and settlement auth lifecycle."""

from __future__ import annotations

from typing import Annotated

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from game_session.main import app as session_app
from game_session.settlement import auth as sa
from game_session.shared import identity
from game_session.shared.identity import get_principal
from runefoble_auth.zitadel import ZitadelAuthService

from tests.helpers.campaign_setup import create_campaign
from tests.helpers.module_state import restored_seam
from tests.helpers.ws_identity import SIGNING_ISSUER

from .conftest import bearer_headers

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


def test_missing_bearer_token_is_refused_without_fallback():
    """A request without a bearer token gets 401 from the route. There is no fallback identity."""
    r = APIRouter(prefix="/api/v1/test_auth_missing")

    @r.get("/whoami")
    async def whoami(u: Annotated[sa.VerifiedPrincipal, Depends(get_principal)]):
        return {"user": u.user_id}

    session_app.include_router(r)
    service = ZitadelAuthService(
        issuer="http://zitadel.test", audience="runefoble-api", internal_url=None
    )
    with restored_seam(
        identity.get_zitadel_auth_service, identity.set_zitadel_auth_service, service, replace=True
    ):
        response = TestClient(session_app).get("/api/v1/test_auth_missing/whoami")
        assert response.status_code == 401


def test_fastapi_route_dependencies(settlement_issuer):
    """Verify FastAPI dependency factories enforce Zanzibar object-level permissions."""
    r = APIRouter(prefix="/api/v1/test_auth")

    @r.get("/h/{s}", dependencies=[Depends(sa.require_haven_builder("s"))])
    async def h_ep(u: Annotated[sa.VerifiedPrincipal, Depends(get_principal)]):
        return {"user": u.user_id}

    @r.get("/e/{e}", dependencies=[Depends(sa.require_establishment_manager("e"))])
    async def e_ep(u: Annotated[sa.VerifiedPrincipal, Depends(get_principal)]):
        return {"user": u.user_id}

    session_app.include_router(r)
    tc = TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )
    builder = bearer_headers(settlement_issuer, "builder")
    intruder = bearer_headers(settlement_issuer, "intruder")

    # The builder founds a haven and builds an establishment through the public routes.
    cid = create_campaign(tc, "builder", issuer=settlement_issuer)
    sid = tc.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Keep", "scale": "village", "districts": ["commons"]},
        headers=builder,
    ).json()["settlement_id"]
    eid = tc.post(
        f"/api/v1/settlements/{sid}/establishments",
        json={"district_id": "commons", "category": "commerce", "name": "Forge"},
        headers=builder,
    ).json()["establishment_id"]

    assert tc.get(f"/api/v1/test_auth/h/{sid}", headers=builder).status_code == 200
    assert tc.get(f"/api/v1/test_auth/e/{eid}", headers=builder).status_code == 200
    assert tc.get(f"/api/v1/test_auth/h/{sid}", headers=intruder).status_code == 403
    assert tc.get(f"/api/v1/test_auth/e/{eid}", headers=intruder).status_code == 403
    assert tc.get(f"/api/v1/test_auth/h/{sid}").status_code == 401


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
