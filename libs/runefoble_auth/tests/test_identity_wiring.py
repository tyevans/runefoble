"""Behaviour of the identity dependency factory (TASK-0712, ADR-0015 c and e).

The tests build a small FastAPI app through the public factory and call it over HTTP.
Tokens come from the signing test issuer, so every verification is real RS256.
"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer
from runefoble_auth.wiring import build_identity_dependencies, make_verifier_holder
from runefoble_auth.zitadel import ZitadelAuthService
from runefoble_platform.errors import ConfigurationError
from runefoble_platform.service_credential import SERVICE_CREDENTIAL_HEADER

SERVICE_TOKEN = "wiring-test-service-credential"


def _app(get_verifier, service_credential: str | None) -> FastAPI:
    deps = build_identity_dependencies(get_verifier, service_credential)
    app = FastAPI()

    @app.get("/me")
    def me(user_id: deps.CallerId) -> dict[str, str]:
        return {"user_id": user_id}

    @app.get("/service", dependencies=[Depends(deps.get_caller_or_service)])
    def service() -> dict[str, bool]:
        return {"ok": True}

    return app


@pytest.fixture
def issuer() -> SigningTestIssuer:
    return SigningTestIssuer()


@pytest.fixture
def get_verifier(issuer: SigningTestIssuer):
    getter, setter = make_verifier_holder(issuer.verifier)
    return getter


def test_request_without_token_is_refused(get_verifier) -> None:
    client = TestClient(_app(get_verifier, SERVICE_TOKEN))
    response = client.get("/me")
    assert response.status_code == 401


def test_forged_token_is_refused(get_verifier) -> None:
    forger = SigningTestIssuer()
    forged = forger.mint("user-mallory")
    client = TestClient(_app(get_verifier, SERVICE_TOKEN))
    response = client.get("/me", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_verified_token_yields_its_subject(get_verifier, issuer: SigningTestIssuer) -> None:
    client = TestClient(_app(get_verifier, SERVICE_TOKEN))
    token = issuer.mint("user-evelyn")
    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"user_id": "user-evelyn"}


def test_service_credential_passes_when_it_matches(get_verifier) -> None:
    client = TestClient(_app(get_verifier, SERVICE_TOKEN))
    response = client.get("/service", headers={SERVICE_CREDENTIAL_HEADER: SERVICE_TOKEN})
    assert response.status_code == 200


def test_service_credential_refused_when_none_is_configured(get_verifier) -> None:
    client = TestClient(_app(get_verifier, None))
    response = client.get("/service", headers={SERVICE_CREDENTIAL_HEADER: SERVICE_TOKEN})
    assert response.status_code == 401


def test_blank_issuer_fails_at_build_time() -> None:
    with pytest.raises(ConfigurationError):
        ZitadelAuthService(issuer=" ", audience="runefoble-api", internal_url=None)


def test_blank_audience_fails_at_build_time() -> None:
    with pytest.raises(ConfigurationError):
        ZitadelAuthService(issuer="http://zitadel.test", audience="", internal_url=None)
