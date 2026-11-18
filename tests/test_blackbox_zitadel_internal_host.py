"""Frontdoor tests for the in-cluster Zitadel verifier (ADR-0015 c).

A pod reaches Zitadel at its in-cluster origin, but Zitadel serves only its external host.
The verifier must send `Host: auth.localhost` on discovery and JWKS requests, and it must
still check `iss` against the external issuer. A local HTTP server plays Zitadel. It
refuses any request whose Host header is not the issuer host.
"""

from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from helpers.local_http_server import LocalHttpServer, RecordedRequest
from runefoble_auth.principal import VerifiedPrincipal, require_principal
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer
from runefoble_auth.zitadel import ZitadelAuthService

ISSUER = "http://auth.localhost"
PROJECT_ID = "364509876543210987"


class FakeZitadel:
    """Serves OIDC discovery and the JWKS of one issuer. Refuses unknown Host headers."""

    def __init__(self, issuer: SigningTestIssuer) -> None:
        self._issuer = issuer

    def __call__(self, request: RecordedRequest) -> tuple[int, object]:
        if request.headers.get("Host") != "auth.localhost":
            return 404, {"message": "Instance not found"}
        if request.path == "/.well-known/openid-configuration":
            return 200, {"issuer": ISSUER, "jwks_uri": f"{ISSUER}/oauth/v2/keys"}
        if request.path == "/oauth/v2/keys":
            return 200, self._issuer.jwks()
        return 404, {"message": "not found"}


@pytest.fixture
def issuer() -> SigningTestIssuer:
    return SigningTestIssuer(issuer=ISSUER, audience=PROJECT_ID)


@pytest.fixture
def zitadel(issuer: SigningTestIssuer):
    fake = FakeZitadel(issuer)
    with LocalHttpServer(fake) as server:
        yield server


def build_app(verifier: ZitadelAuthService) -> FastAPI:
    app = FastAPI()
    get_principal = require_principal(lambda: verifier)

    @app.get("/me")
    def me(principal: Annotated[VerifiedPrincipal, Depends(get_principal)]) -> dict[str, object]:
        return principal.model_dump()

    return app


def in_cluster_verifier(zitadel_url: str) -> ZitadelAuthService:
    return ZitadelAuthService(issuer=ISSUER, audience=PROJECT_ID, internal_url=zitadel_url)


def test_token_from_the_external_issuer_is_accepted_through_the_in_cluster_origin(
    issuer: SigningTestIssuer, zitadel: LocalHttpServer
) -> None:
    client = TestClient(build_app(in_cluster_verifier(zitadel.url)))
    token = issuer.mint("user-evelyn", audience=PROJECT_ID)

    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["user_id"] == "user-evelyn"


def test_discovery_and_jwks_requests_name_the_issuer_host(
    issuer: SigningTestIssuer, zitadel: LocalHttpServer
) -> None:
    client = TestClient(build_app(in_cluster_verifier(zitadel.url)))
    token = issuer.mint("user-evelyn", audience=PROJECT_ID)

    client.get("/me", headers={"Authorization": f"Bearer {token}"})

    fetched = [
        req
        for req in zitadel.requests
        if req.path in ("/.well-known/openid-configuration", "/oauth/v2/keys")
    ]
    assert {req.path for req in fetched} == {"/.well-known/openid-configuration", "/oauth/v2/keys"}
    assert {req.headers.get("Host") for req in fetched} == {"auth.localhost"}


def test_token_for_another_audience_is_refused(
    issuer: SigningTestIssuer, zitadel: LocalHttpServer
) -> None:
    client = TestClient(build_app(in_cluster_verifier(zitadel.url)))
    token = issuer.mint("user-evelyn", audience="some-other-project")

    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_token_with_another_issuer_is_refused_even_though_keys_match(
    issuer: SigningTestIssuer, zitadel: LocalHttpServer
) -> None:
    client = TestClient(build_app(in_cluster_verifier(zitadel.url)))
    token = issuer.mint("user-evelyn", audience=PROJECT_ID, issuer="http://zitadel:8080")

    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
