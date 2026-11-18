"""Blackbox frontdoor suite: every public surface refuses every class of bad credential (TASK-0535).

Governed by:
- ADR-0014: BDD and frontdoor blackbox tests (Hard Invariant 7)
- ADR-0015 (c): every service verifies the Zitadel JWT itself
- US-0062: sign-in must refuse invalid credentials
- US-0013: every gateway call uses a verified subject

Each case sends one public request with one bad credential and asserts one observable
refusal. HTTP must answer 401 with `WWW-Authenticate: Bearer`. A WebSocket handshake must
close with 1008 before accept. Positive controls prove that the trusted issuer really is
wired in, so a refusal cannot come from a missing trust setup.

Tokens use the public token format only. `SigningTestIssuer` mints signed tokens. Tokens that
the trusted issuer would never sign come from PyJWT or raw base64, as an attacker would build them.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Callable, Iterator
from typing import Any

import jwt
import pytest
from board_state.main import app as board_app
from campaign_lore.main import app as lore_app
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from rules_compendium.main import app as compendium_app
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer
from starlette.websockets import WebSocketDisconnect
from voice_agent.main import app as voice_app

from tests.helpers.silo_fixtures import PNG_SAMPLE_BYTES
from tests.helpers.ws_identity import SIGNING_ISSUER

WS_POLICY_VIOLATION = 1008
RUNEFOBLE_PROTOCOL = "runefoble.v1"
PROBE_SUBJECT = "user-negative-probe"
CONTROL_SUBJECT = "user-negative-control"
KNOWN_SECRET = "attacker-known-secret-0123456789abcdef"
ISSUER = SIGNING_ISSUER.issuer
AUDIENCE = SIGNING_ISSUER.audience
KID = SIGNING_ISSUER.kid


@pytest.fixture(autouse=True)
def dev_mode_flags_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """The retired dev-mode flags are set for every case. They must grant nothing (ADR-0015)."""
    monkeypatch.setenv("RUNEFOBLE_AUTH_DEV_MODE", "true")
    monkeypatch.setenv("AUTH_DEV_MODE", "true")


@pytest.fixture(autouse=True)
def trusted_surfaces(trusted_ws_issuer, trusted_voice_issuer) -> None:
    """Trust the shared test issuer in the gateway and voice_agent verifiers for each case."""


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _claims(**overrides: Any) -> dict[str, Any]:
    now = int(time.time())
    claims: dict[str, Any] = {
        "sub": PROBE_SUBJECT,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + 3600,
    }
    claims.update(overrides)
    return claims


def _public_pem() -> bytes:
    return SIGNING_ISSUER.private_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )


def _unsigned_token() -> str:
    header = _b64(json.dumps({"alg": "RS256", "typ": "JWT", "kid": KID}).encode())
    return f"{header}.{_b64(json.dumps(_claims()).encode())}."


def _hs256_keyed_with_public_key() -> str:
    """Sign HS256 with the trusted public key PEM as the HMAC secret (the algorithm-confusion attack).

    PyJWT refuses to sign this way, so the attacker's HMAC is computed by hand.
    """
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT", "kid": KID}).encode())
    payload = _b64(json.dumps(_claims()).encode())
    signing_input = f"{header}.{payload}".encode()
    signature = hmac.new(_public_pem(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64(signature)}"


def _missing_sub_token() -> str:
    claims = _claims()
    del claims["sub"]
    return jwt.encode(claims, SIGNING_ISSUER.private_key, algorithm="RS256", headers={"kid": KID})


# Each factory returns the raw bearer value, or None for "no credential".
BAD_CREDENTIALS: dict[str, Callable[[], str | None]] = {
    "no-credential": lambda: None,
    "garbage-string": lambda: "not-a-jwt",
    "hs256-known-secret": lambda: jwt.encode(
        _claims(), KNOWN_SECRET, algorithm="HS256", headers={"kid": KID}
    ),
    "hs256-public-key-as-secret": _hs256_keyed_with_public_key,
    "alg-none": lambda: jwt.encode(_claims(), None, algorithm="none", headers={"kid": KID}),
    "unsigned": _unsigned_token,
    "rs256-unknown-key": lambda: SigningTestIssuer(issuer=ISSUER, kid=KID).mint(PROBE_SUBJECT),
    "expired": lambda: SIGNING_ISSUER.mint(PROBE_SUBJECT, expires_in=-60),
    "wrong-audience": lambda: SIGNING_ISSUER.mint(PROBE_SUBJECT, audience="runefoble-other-api"),
    "sibling-service-audience": lambda: SIGNING_ISSUER.mint(
        PROBE_SUBJECT, audience="runefoble-board-state"
    ),
    "wrong-issuer": lambda: SIGNING_ISSUER.mint(PROBE_SUBJECT, issuer="http://evil-zitadel.test"),
    "missing-sub": _missing_sub_token,
}


def _bearer_headers(token: str | None) -> dict[str, str]:
    return {} if token is None else {"Authorization": f"Bearer {token}"}


def _ws_protocols(token: str | None) -> list[str]:
    if token is None:
        return [RUNEFOBLE_PROTOCOL]
    return [RUNEFOBLE_PROTOCOL, f"runefoble.bearer.{token}"]


def _upload(client: TestClient, headers: dict[str, str]):
    return client.post(
        "/api/v1/assets/upload",
        files={"file": ("probe.png", PNG_SAMPLE_BYTES, "image/png")},
        data={"asset_type": "avatar"},
        headers=headers,
    )


def _get(path: str) -> Callable[[TestClient, dict[str, str]], Any]:
    return lambda client, headers: client.get(path, headers=headers)


@pytest.fixture
def gateway_client(game_session_upstream, asset_forge_upstream) -> Iterator[TestClient]:
    """Enter the gateway lifespan after game_session and asset_forge serve, so proxies reach them."""
    with TestClient(gateway_app) as client:
        yield client


@pytest.fixture(scope="module")
def compendium_client() -> Iterator[TestClient]:
    """Enter the compendium lifespan, which builds the retrieval engine that spell routes read."""
    with TestClient(compendium_app) as client:
        yield client


# Each HTTP surface: the app that owns the route, the fixture that yields its client (None
# means a bare TestClient), and one request to the route.
HTTP_SURFACES: dict[str, tuple[Any, str | None, Callable[[TestClient, dict[str, str]], Any]]] = {
    "gateway-profile": (gateway_app, "gateway_client", _get("/api/v1/profile")),
    "gateway-campaign-create": (
        gateway_app,
        "gateway_client",
        lambda client, headers: client.post(
            "/api/v1/campaigns",
            json={"title": "Ghost Campaign", "setting": "Nowhere"},
            headers=headers,
        ),
    ),
    "gateway-asset-upload": (gateway_app, "gateway_client", _upload),
    "board-state-read": (board_app, None, _get("/api/v1/boards/sess-negative-probe")),
    "campaign-lore-document-read": (
        lore_app,
        None,
        _get("/api/v1/lore/documents/doc-negative-probe"),
    ),
    "rules-compendium-spell": (
        compendium_app,
        "compendium_client",
        _get("/api/v1/compendium/spells/Fireball"),
    ),
    "voice-agent-presets": (voice_app, None, _get("/api/v1/voice/presets")),
}


def _surface_client(
    request: pytest.FixtureRequest, app: Any, fixture_name: str | None
) -> TestClient:
    if fixture_name is None:
        return TestClient(app)
    client: TestClient = request.getfixturevalue(fixture_name)
    return client


WS_SESSION_PATH = "/ws/session/sess-negative-probe"
WS_CONTROL_PATH = "/ws/campaigns/camp-negative-probe"
RETIRED_ROUTES = [
    ("POST", "/api/v1/auth/token"),
    ("POST", "/api/v1/auth/admin/seed"),
    ("POST", "/api/v1/auth/sync/user"),
]


@pytest.mark.parametrize("credential", list(BAD_CREDENTIALS))
@pytest.mark.parametrize("surface", list(HTTP_SURFACES))
def test_http_surface_refuses_bad_credential(
    request: pytest.FixtureRequest, surface: str, credential: str
) -> None:
    app, fixture_name, send = HTTP_SURFACES[surface]
    token = BAD_CREDENTIALS[credential]()

    response = send(_surface_client(request, app, fixture_name), _bearer_headers(token))

    assert response.status_code == 401, response.text
    assert response.headers.get("www-authenticate") == "Bearer"


@pytest.mark.parametrize("credential", list(BAD_CREDENTIALS))
def test_websocket_handshake_refuses_bad_credential(credential: str) -> None:
    token = BAD_CREDENTIALS[credential]()
    client = TestClient(gateway_app)

    with (
        pytest.raises(WebSocketDisconnect) as refused,
        client.websocket_connect(WS_SESSION_PATH, subprotocols=_ws_protocols(token)),
    ):
        pass

    assert refused.value.code == WS_POLICY_VIOLATION


@pytest.mark.parametrize("surface", list(HTTP_SURFACES))
def test_http_surface_admits_valid_control_token(
    request: pytest.FixtureRequest, surface: str
) -> None:
    """Control: a valid token passes the gate, so the refusals above are not a broken setup."""
    app, fixture_name, send = HTTP_SURFACES[surface]
    token = SIGNING_ISSUER.mint(CONTROL_SUBJECT)

    response = send(_surface_client(request, app, fixture_name), _bearer_headers(token))

    assert response.status_code != 401, response.text


def test_websocket_admits_valid_control_token() -> None:
    token = SIGNING_ISSUER.mint(CONTROL_SUBJECT)
    client = TestClient(gateway_app)

    with client.websocket_connect(WS_CONTROL_PATH, subprotocols=_ws_protocols(token)) as ws:
        assert ws.accepted_subprotocol == RUNEFOBLE_PROTOCOL


@pytest.mark.parametrize(("method", "path"), RETIRED_ROUTES)
def test_retired_identity_route_is_gone_even_with_valid_token(method: str, path: str) -> None:
    """The retired sign-in, seed and body-claim sync routes do not exist (ADR-0015)."""
    token = SIGNING_ISSUER.mint(PROBE_SUBJECT)
    body = {"user_id": "user-victim", "roles": ["owner", "dungeon_master"]}
    client = TestClient(gateway_app)

    response = client.request(method, path, json=body, headers=_bearer_headers(token))

    assert response.status_code in (404, 405), response.text


@pytest.mark.parametrize(("method", "path"), RETIRED_ROUTES)
def test_retired_identity_route_refuses_anonymous_call(method: str, path: str) -> None:
    client = TestClient(gateway_app)

    response = client.request(method, path, json={"user_id": "user-victim"})

    assert response.status_code in (404, 405), response.text
