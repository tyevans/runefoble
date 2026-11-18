"""Shared fixtures and harness for Campaign and Session Lobby blackbox tests.

Governed by ADR-0001, ADR-0003, ADR-0006, and Hard Invariants 6 and 7.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient
from game_session.main import app as session_app
from gateway_api.main import app as gateway_app

from tests.helpers.ws_identity import SIGNING_ISSUER


def auth_headers(sub: str) -> dict[str, str]:
    """Return Bearer headers for a token that the service verifier accepts."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def client_gw(game_session_upstream, character_sheet_upstream) -> Iterator[TestClient]:
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


@pytest.fixture
def client_sess(game_session_upstream) -> Iterator[TestClient]:
    with TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    ) as session_client:
        yield session_client


@pytest.fixture
def client_char(game_session_upstream) -> Iterator[TestClient]:
    with TestClient(character_app, headers=auth_headers("character-owner")) as character_client:
        yield character_client


@pytest.fixture
def open_session(client_gw: TestClient, client_sess: TestClient):
    """Return a function that creates a campaign and a lobby session for an owner, over HTTP."""

    def _open(owner: str) -> str:
        campaign = client_gw.post(
            "/api/v1/campaigns", json={"title": f"{owner} table"}, headers=auth_headers(owner)
        )
        assert campaign.status_code == 201, campaign.text
        session = client_sess.post(
            "/api/v1/sessions/create",
            json={"campaign_id": campaign.json()["id"], "title": "Night", "dm_id": owner},
            headers=auth_headers(owner),
        )
        assert session.status_code == 200, session.text
        return session.json()["session_id"]

    return _open
