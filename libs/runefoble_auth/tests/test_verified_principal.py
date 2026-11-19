"""Frontdoor tests for the verified-principal dependency and the WebSocket handshake helper.

Each test drives a minimal FastAPI app through HTTP or WebSocket. No test
reaches into verifier internals.
"""

import time
from typing import Annotated

import jwt
import pytest
from fastapi import Depends, FastAPI, WebSocket
from fastapi.testclient import TestClient
from runefoble_auth.principal import VerifiedPrincipal, require_principal
from runefoble_auth.websocket import (
    RUNEFOBLE_SUBPROTOCOL,
    WebSocketAuthError,
    authenticate_websocket,
)
from runefoble_auth.zitadel import ZitadelAuthService
from starlette.websockets import WebSocketDisconnect

from tests.helpers.signing_test_issuer import SigningTestIssuer

KNOWN_SECRET = "attacker-known-secret-value-32-bytes!"


@pytest.fixture
def issuer() -> SigningTestIssuer:
    return SigningTestIssuer()


def build_app(verifier: ZitadelAuthService) -> FastAPI:
    app = FastAPI()
    get_principal = require_principal(lambda: verifier)

    @app.get("/me")
    def me(principal: Annotated[VerifiedPrincipal, Depends(get_principal)]) -> dict[str, object]:
        return principal.model_dump()

    @app.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        try:
            principal = authenticate_websocket(websocket, verifier)
        except WebSocketAuthError:
            await websocket.close(code=4401)
            return
        await websocket.accept(subprotocol=RUNEFOBLE_SUBPROTOCOL)
        await websocket.send_json({"user_id": principal.user_id})
        await websocket.close()

    return app


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def assert_unauthorized(response) -> None:  # type: ignore[no-untyped-def]
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


# --- HTTP dependency: accepted tokens -------------------------------------------------


def test_valid_rs256_token_yields_verified_principal(issuer: SigningTestIssuer) -> None:
    client = TestClient(build_app(issuer.verifier()))
    token = issuer.mint("user-evelyn", username="evelyn", email="evelyn@example.test")

    response = client.get("/me", headers=bearer(token))

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "user-evelyn",
        "username": "evelyn",
        "email": "evelyn@example.test",
    }


def test_principal_carries_no_roles_or_admin_flag(issuer: SigningTestIssuer) -> None:
    client = TestClient(build_app(issuer.verifier()))
    token = issuer.mint(
        "user-mallory",
        extra_claims={"urn:zitadel:iam:org:project:roles": {"admin": {}}},
    )

    body = client.get("/me", headers=bearer(token)).json()

    assert set(body) == {"user_id", "username", "email"}


# --- HTTP dependency: rejected tokens --------------------------------------------------


def test_missing_authorization_header_is_rejected(issuer: SigningTestIssuer) -> None:
    client = TestClient(build_app(issuer.verifier()))
    assert_unauthorized(client.get("/me"))


def test_garbage_bearer_value_is_rejected(issuer: SigningTestIssuer) -> None:
    client = TestClient(build_app(issuer.verifier()))
    assert_unauthorized(client.get("/me", headers=bearer("not-a-real-jwt")))


def test_non_bearer_scheme_is_rejected(issuer: SigningTestIssuer) -> None:
    client = TestClient(build_app(issuer.verifier()))
    token = issuer.mint("user-evelyn")
    assert_unauthorized(client.get("/me", headers={"Authorization": f"Basic {token}"}))


def test_hs256_token_signed_with_known_secret_is_rejected(issuer: SigningTestIssuer) -> None:
    client = TestClient(build_app(issuer.verifier()))
    forged = jwt.encode(
        {
            "sub": "user-admin",
            "iss": issuer.issuer,
            "aud": issuer.audience,
            "exp": time.time() + 600,
        },
        KNOWN_SECRET,
        algorithm="HS256",
        headers={"kid": issuer.kid},
    )
    assert_unauthorized(client.get("/me", headers=bearer(forged)))


def test_unsigned_token_with_trusted_kid_is_rejected(issuer: SigningTestIssuer) -> None:
    client = TestClient(build_app(issuer.verifier()))
    forged = jwt.encode(
        {
            "sub": "user-dm-evelyn",
            "iss": issuer.issuer,
            "aud": issuer.audience,
            "exp": time.time() + 600,
        },
        key=None,
        algorithm="none",
        headers={"kid": issuer.kid},
    )
    assert_unauthorized(client.get("/me", headers=bearer(forged)))


def test_alg_none_token_without_kid_is_rejected(issuer: SigningTestIssuer) -> None:
    client = TestClient(build_app(issuer.verifier()))
    forged = jwt.encode(
        {
            "sub": "user-dm-evelyn",
            "iss": issuer.issuer,
            "aud": issuer.audience,
            "exp": time.time() + 600,
        },
        key=None,
        algorithm="none",
    )
    assert_unauthorized(client.get("/me", headers=bearer(forged)))


def test_rs256_token_from_unknown_key_is_rejected(issuer: SigningTestIssuer) -> None:
    client = TestClient(build_app(issuer.verifier()))
    attacker = SigningTestIssuer(issuer=issuer.issuer, audience=issuer.audience, kid=issuer.kid)
    assert_unauthorized(client.get("/me", headers=bearer(attacker.mint("user-attacker"))))


def test_expired_token_is_rejected(issuer: SigningTestIssuer) -> None:
    client = TestClient(build_app(issuer.verifier()))
    assert_unauthorized(
        client.get("/me", headers=bearer(issuer.mint("user-evelyn", expires_in=-60)))
    )


def test_wrong_audience_is_rejected(issuer: SigningTestIssuer) -> None:
    client = TestClient(build_app(issuer.verifier()))
    assert_unauthorized(
        client.get("/me", headers=bearer(issuer.mint("user-evelyn", audience="other-service")))
    )


def test_wrong_issuer_is_rejected(issuer: SigningTestIssuer) -> None:
    client = TestClient(build_app(issuer.verifier()))
    assert_unauthorized(
        client.get("/me", headers=bearer(issuer.mint("user-evelyn", issuer="http://evil.test")))
    )


def test_missing_subject_is_rejected(issuer: SigningTestIssuer) -> None:
    client = TestClient(build_app(issuer.verifier()))
    token = jwt.encode(
        {"iss": issuer.issuer, "aud": issuer.audience, "exp": time.time() + 600},
        issuer.private_key,
        algorithm="RS256",
        headers={"kid": issuer.kid},
    )
    assert_unauthorized(client.get("/me", headers=bearer(token)))


def test_empty_subject_is_rejected(issuer: SigningTestIssuer) -> None:
    client = TestClient(build_app(issuer.verifier()))
    assert_unauthorized(client.get("/me", headers=bearer(issuer.mint(""))))


def test_legacy_bypass_environment_flags_do_not_admit_requests(
    issuer: SigningTestIssuer, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RUNEFOBLE_AUTH_DEV_MODE", "true")
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    client = TestClient(build_app(issuer.verifier()))

    assert_unauthorized(client.get("/me"))
    assert_unauthorized(client.get("/me", headers=bearer("not-a-real-jwt")))


# --- WebSocket handshake ---------------------------------------------------------------


def test_websocket_with_valid_bearer_subprotocol_is_accepted(issuer: SigningTestIssuer) -> None:
    client = TestClient(build_app(issuer.verifier()))
    token = issuer.mint("user-evelyn")

    with client.websocket_connect(
        "/ws", subprotocols=[RUNEFOBLE_SUBPROTOCOL, f"runefoble.bearer.{token}"]
    ) as session:
        assert session.receive_json() == {"user_id": "user-evelyn"}


def test_websocket_without_bearer_subprotocol_is_denied_before_accept(
    issuer: SigningTestIssuer,
) -> None:
    client = TestClient(build_app(issuer.verifier()))

    with (
        pytest.raises(WebSocketDisconnect) as excinfo,
        client.websocket_connect("/ws", subprotocols=[RUNEFOBLE_SUBPROTOCOL]),
    ):
        pass
    assert excinfo.value.code == 4401


def test_websocket_with_forged_bearer_subprotocol_is_denied(issuer: SigningTestIssuer) -> None:
    client = TestClient(build_app(issuer.verifier()))
    forged = jwt.encode(
        {
            "sub": "user-dm-evelyn",
            "iss": issuer.issuer,
            "aud": issuer.audience,
            "exp": time.time() + 600,
        },
        KNOWN_SECRET,
        algorithm="HS256",
        headers={"kid": issuer.kid},
    )

    with (
        pytest.raises(WebSocketDisconnect) as excinfo,
        client.websocket_connect(
            "/ws", subprotocols=[RUNEFOBLE_SUBPROTOCOL, f"runefoble.bearer.{forged}"]
        ),
    ):
        pass
    assert excinfo.value.code == 4401


def test_websocket_token_in_query_string_is_not_accepted(issuer: SigningTestIssuer) -> None:
    client = TestClient(build_app(issuer.verifier()))
    token = issuer.mint("user-evelyn")

    with (
        pytest.raises(WebSocketDisconnect) as excinfo,
        client.websocket_connect(f"/ws?token={token}", subprotocols=[RUNEFOBLE_SUBPROTOCOL]),
    ):
        pass
    assert excinfo.value.code == 4401
