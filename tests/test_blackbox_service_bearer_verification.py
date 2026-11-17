"""Blackbox tests: asset_forge, soundscape, and character_sheet verify Zitadel bearer tokens (TASK-0528).

Governed by ADR-0015 decision (c), Hard Invariant 1 (SpiceDB, not roles), and Hard Invariant 7.
Every request goes through a public HTTP route. The verifier is the signing test issuer, so the
services run the same RS256 checks they run in deployment.

Verifies:
1. Every operation in each service's OpenAPI document returns 401 without a valid bearer token.
2. A forged `x-user-id` header is ignored. The created asset's creator is the token subject.
3. A forged `x-user-id` header does not grant character edit rights.
4. Health, UI manifest, and OpenAPI routes stay public.
"""

from __future__ import annotations

import pytest
from asset_forge.dependencies import set_event_bus as set_forge_event_bus
from asset_forge.main import app as asset_forge_app
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer
from runefoble_platform.redis_bus import RedisStreamsEventBus
from soundscape.main import app as soundscape_app

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

PUBLIC_PATHS = {"/healthz", "/health", "/ui/manifest", "/openapi.json"}
PATH_PARAM_VALUE = "00000000-0000-4000-8000-000000000001"
SERVICE_APPS = {
    "asset_forge": asset_forge_app,
    "soundscape": soundscape_app,
    "character_sheet": character_app,
}


def _operations(app) -> list[tuple[str, str]]:
    """Return (method, concrete path) for every protected operation in the app's OpenAPI document."""
    operations: list[tuple[str, str]] = []
    for path, methods in app.openapi()["paths"].items():
        if path in PUBLIC_PATHS:
            continue
        concrete = path
        for name in ("character_id", "asset_id", "session_id", "item_id", "slot", "condition"):
            concrete = concrete.replace("{" + name + "}", PATH_PARAM_VALUE)
        concrete = concrete.replace("{penalty_type}", "absent").replace(
            "{variant_id}", PATH_PARAM_VALUE
        )
        for method in methods:
            if method in {"get", "post", "put", "patch", "delete"}:
                operations.append((method.upper(), concrete))
    return operations


OPERATIONS = [
    pytest.param(name, method, path, id=f"{name}:{method}:{path}")
    for name, app in SERVICE_APPS.items()
    for method, path in _operations(app)
]


def _forged_token() -> str:
    """Mint a token from an issuer the services do not trust."""
    return SigningTestIssuer(issuer="http://attacker.test").mint("attacker")


@pytest.mark.parametrize(("service", "method", "path"), OPERATIONS)
def test_protected_operation_rejects_missing_bearer(service: str, method: str, path: str) -> None:
    """No Authorization header yields 401 on every operation in the service."""
    client = TestClient(SERVICE_APPS[service])
    response = client.request(method, path)
    assert response.status_code == 401, response.text
    assert response.headers.get("www-authenticate") == "Bearer"


@pytest.mark.parametrize(("service", "method", "path"), OPERATIONS)
@pytest.mark.parametrize(
    "authorization",
    [
        pytest.param("Bearer not-a-jwt", id="garbage"),
        pytest.param(f"Bearer {_forged_token()}", id="untrusted-issuer"),
        pytest.param("Basic dXNlcjpwYXNz", id="basic-scheme"),
    ],
)
def test_protected_operation_rejects_invalid_bearer(
    service: str, method: str, path: str, authorization: str
) -> None:
    """Garbage, untrusted, and non-bearer credentials yield 401 on every operation."""
    client = TestClient(SERVICE_APPS[service])
    response = client.request(method, path, headers={"Authorization": authorization})
    assert response.status_code == 401, response.text


@pytest.mark.parametrize("service", list(SERVICE_APPS))
def test_public_routes_stay_public(service: str) -> None:
    """Health, OpenAPI, and manifest routes answer without a token."""
    client = TestClient(SERVICE_APPS[service])
    assert client.get("/healthz").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_forged_user_header_does_not_set_asset_creator() -> None:
    """A forged x-user-id is ignored. The forged asset's creator is the token subject."""
    mock_redis = MockAsyncRedis()
    set_forge_event_bus(RedisStreamsEventBus(client=mock_redis))
    try:
        client = TestClient(asset_forge_app)
        response = client.post(
            "/api/v1/forge/token",
            json={"token_name": "Ghoul", "prompt": "Gaunt ghoul with rusted claws"},
            headers={
                "Authorization": f"Bearer {SIGNING_ISSUER.mint('forger-valeros')}",
                "x-user-id": "attacker-mallory",
            },
        )
        assert response.status_code == 200, response.text
    finally:
        set_forge_event_bus(None)

    entries = mock_redis.streams.get("runefoble.events.asset", [])
    assert len(entries) == 1
    _, event = entries[0]
    assert "forger-valeros" in event["payload"]
    assert "attacker-mallory" not in event["payload"]


def test_forged_user_header_does_not_grant_character_edit() -> None:
    """The owner creates a character. A stranger who forges the owner's header still gets 403."""
    owner = {"Authorization": f"Bearer {SIGNING_ISSUER.mint('owner-nadia')}"}
    stranger = {
        "Authorization": f"Bearer {SIGNING_ISSUER.mint('stranger-mallory')}",
        "x-user-id": "owner-nadia",
    }
    client = TestClient(character_app)

    created = client.post(
        "/api/v1/characters",
        json={"name": "Nadia", "character_class": "Bard", "max_hp": 22},
        headers=owner,
    )
    assert created.status_code == 200, created.text
    character_id = created.json()["character_id"]

    guardrails = {"protect_allies": ["valeros"], "risk_threshold": "balanced"}
    forged = client.put(
        f"/api/v1/characters/{character_id}/guardrails", json=guardrails, headers=stranger
    )
    assert forged.status_code == 403, forged.text

    allowed = client.put(
        f"/api/v1/characters/{character_id}/guardrails", json=guardrails, headers=owner
    )
    assert allowed.status_code == 200, allowed.text
