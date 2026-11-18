"""Blackbox frontdoor tests: board_state, rules_compendium, and campaign_analytics verify bearers.

Governed by ADR-0015 (decision c), US-0013, and Hard Invariants 1 and 7. Every case drives a
public HTTP route. Identity comes only from a bearer token that the service verifies itself.
A token signed by an untrusted key, a garbage token, and a spoofed `x-user-id` header never
grant identity. Authorization setup uses the SpiceDB double that the services read.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from board_state.main import app as board_app
from campaign_analytics.main import app as analytics_app
from fastapi.testclient import TestClient
from rules_compendium.dependencies import get_spicedb_client
from rules_compendium.main import app as compendium_app
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer

from tests.helpers.ws_identity import SIGNING_ISSUER

UNTRUSTED_ISSUER = SigningTestIssuer()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _protected_calls(campaign_id: str) -> list[tuple[str, str, str, dict | None]]:
    """(service, method, path, json body) for one route per router in each token-verifying service."""
    return [
        ("board", "POST", "/api/v1/boards", {"session_id": "guard-probe", "cols": 4, "rows": 4}),
        ("board", "GET", "/api/v1/boards/guard-probe", None),
        ("board", "POST", "/api/v1/boards/guard-probe/traps", {"trap_id": "t"}),
        ("compendium", "GET", "/api/v1/compendium/rules/search?query=fire", None),
        ("compendium", "GET", "/api/v1/compendium/monsters/goblin", None),
        (
            "compendium",
            "POST",
            "/api/v1/compendium/homebrew",
            {"campaign_id": campaign_id, "rule_type": "monster", "title": "X", "content": {}},
        ),
        ("compendium", "GET", f"/api/v1/compendium/homebrew/{campaign_id}", None),
        ("analytics", "GET", f"/api/v1/analytics/campaigns/{campaign_id}/heatmap", None),
        ("analytics", "GET", f"/api/v1/analytics/campaigns/{campaign_id}/mvp", None),
        ("analytics", "GET", f"/api/v1/analytics/campaigns/{campaign_id}/timeline", None),
    ]


SERVICE_APPS = {"board": board_app, "compendium": compendium_app, "analytics": analytics_app}


def _anonymous(service: str) -> TestClient:
    return TestClient(SERVICE_APPS[service])


@pytest.mark.parametrize(
    "credential",
    [
        pytest.param(None, id="no-bearer"),
        pytest.param("not-a-jwt", id="garbage-token"),
        pytest.param(UNTRUSTED_ISSUER.mint("dm1"), id="forged-token-from-untrusted-key"),
    ],
)
def test_protected_routes_refuse_missing_or_forged_bearer(credential: str | None) -> None:
    """Every protected route in the three services returns 401 without a verified bearer."""
    campaign_id = str(uuid4())
    for service, method, path, body in _protected_calls(campaign_id):
        headers = {} if credential is None else _auth(credential)
        client = TestClient(SERVICE_APPS[service], headers=headers)
        res = client.request(method, path, json=body)
        assert res.status_code == 401, f"{service} {method} {path} returned {res.status_code}"
        assert res.headers.get("www-authenticate") == "Bearer"


PUBLIC_ROUTES = [
    ("board", "/healthz"),
    ("board", "/openapi.json"),
    ("board", "/ui/manifest"),
    ("compendium", "/health"),
    ("compendium", "/healthz"),
    ("compendium", "/openapi.json"),
    ("compendium", "/ui/manifest"),
    ("analytics", "/health"),
    ("analytics", "/healthz"),
    ("analytics", "/openapi.json"),
    ("analytics", "/ui/manifest"),
]


@pytest.mark.parametrize(("service", "path"), PUBLIC_ROUTES)
def test_health_openapi_and_manifest_stay_public(service: str, path: str) -> None:
    """Health, OpenAPI, and microfrontend discovery need no bearer. Other routes do."""
    res = _anonymous(service).get(path)
    assert res.status_code == 200, f"{service} {path} returned {res.status_code}"


@pytest.mark.asyncio
async def test_spoofed_user_header_is_ignored_and_token_subject_is_recorded() -> None:
    """A valid bearer for dm1 with `x-user-id: dm2` writes the homebrew rule as dm1."""
    campaign_id = str(uuid4())
    await get_spicedb_client().write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="dungeon_master",
        subject_type="user",
        subject_id="dm1",
    )
    with TestClient(compendium_app, headers=_auth(SIGNING_ISSUER.mint("dm1"))) as client:
        res = client.post(
            "/api/v1/compendium/homebrew",
            json={
                "campaign_id": campaign_id,
                "rule_type": "monster",
                "title": "Spoof Probe",
                "content": {"challenge_rating": 1.0},
            },
            headers={"x-user-id": "dm2"},
        )
    assert res.status_code == 200, res.text
    assert res.json()["author_id"] == "dm1"


def test_valid_token_without_campaign_permission_is_forbidden() -> None:
    """A verified stranger gets 403 from the SpiceDB check, not an anonymous pass."""
    campaign_id = str(uuid4())
    with TestClient(compendium_app, headers=_auth(SIGNING_ISSUER.mint("stranger"))) as client:
        res = client.post(
            "/api/v1/compendium/homebrew",
            json={"campaign_id": campaign_id, "rule_type": "monster", "title": "Y", "content": {}},
        )
    assert res.status_code == 403
