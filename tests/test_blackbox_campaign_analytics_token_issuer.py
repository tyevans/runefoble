"""Blackbox tests: Campaign Analytics verifies tokens against the settings it was built with.

TASK-0880 and ADR-0015 (c). Two apps come from `create_app` with two issuers. Each app accepts
a token from its own issuer and refuses a token from the other issuer with 401. A local
stand-in serves the discovery and JWKS of both issuers, so the verifier runs its real checks.
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from campaign_analytics.main import create_app
from fastapi import FastAPI
from fastapi.testclient import TestClient
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import EventBusProvider

from tests.helpers.campaign_analytics_service import AnalyticsService
from tests.helpers.zitadel_stand_in import zitadel_stand_in

FIRST_ISSUER = SigningTestIssuer(issuer="http://issuer-first.test", audience="runefoble-api")
SECOND_ISSUER = SigningTestIssuer(issuer="http://issuer-second.test", audience="runefoble-api")


def _app_for(
    monkeypatch: pytest.MonkeyPatch, issuer: SigningTestIssuer, internal_url: str
) -> FastAPI:
    """Build one app from settings that name `issuer`. The app keeps its own verifier."""
    monkeypatch.setenv("RUNEFOBLE_ZITADEL_ISSUER", issuer.issuer)
    monkeypatch.setenv("RUNEFOBLE_ZITADEL_AUDIENCE", issuer.audience)
    monkeypatch.setenv("RUNEFOBLE_ZITADEL_INTERNAL_URL", internal_url)
    settings = PlatformSettings()
    return create_app(settings, EventBusProvider(settings))


@pytest.fixture
def first_app_and_second_app(
    analytics_service: AnalyticsService, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[FastAPI, FastAPI]]:
    with zitadel_stand_in(FIRST_ISSUER, SECOND_ISSUER) as stand_in:
        first = _app_for(monkeypatch, FIRST_ISSUER, stand_in.url)
        second = _app_for(monkeypatch, SECOND_ISSUER, stand_in.url)
        yield first, second


def _status_with_token(app: FastAPI, token: str) -> int:
    """Call one protected route. The app runs without its lifespan, so a verified caller
    stops at the store, not at the verifier. Only a 401 means the verifier refused the token."""
    client = TestClient(app)
    res = client.get(
        f"/api/v1/analytics/campaigns/{uuid4()}/heatmap",
        headers={"Authorization": f"Bearer {token}"},
    )
    return res.status_code


def test_each_app_accepts_a_token_from_its_own_issuer(
    first_app_and_second_app: tuple[FastAPI, FastAPI],
) -> None:
    """A token minted by the app's own issuer passes verification."""
    first_app, second_app = first_app_and_second_app

    assert _status_with_token(first_app, FIRST_ISSUER.mint("player-first")) != 401
    assert _status_with_token(second_app, SECOND_ISSUER.mint("player-second")) != 401


def test_each_app_refuses_a_token_from_the_other_issuer(
    first_app_and_second_app: tuple[FastAPI, FastAPI],
) -> None:
    """A token from the other issuer fails the `iss` check, so the app answers 401."""
    first_app, second_app = first_app_and_second_app

    assert _status_with_token(first_app, SECOND_ISSUER.mint("player-second")) == 401
    assert _status_with_token(second_app, FIRST_ISSUER.mint("player-first")) == 401
