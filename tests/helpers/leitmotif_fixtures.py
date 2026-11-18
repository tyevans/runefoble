"""Shared fixtures and helper utilities for character leitmotif blackbox tests.

Governed by:
- ADR-0002, ADR-0003, ADR-0006, ADR-0013
- Hard Invariant 1 (SpiceDB Zanzibar), Hard Invariant 6 (File length < 500 lines)
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from soundscape.main import app

from tests.helpers.ws_identity import SIGNING_ISSUER


def auth_headers(sub: str) -> dict[str, str]:
    """Return Bearer headers for a token that the service verifier accepts."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, headers=auth_headers("soundscape-tester"))


@pytest.fixture(name="leitmotif_session_id")
def leitmotif_session_id_fixture(trusted_ws_issuer, game_session_upstream) -> Iterator[str]:
    """Create a campaign and a session through the gateway frontdoor. The default subject owns both.

    The gateway proxies to the live game_session upstream, so the client enters the gateway lifespan.
    """
    with TestClient(gateway_app) as gateway:
        campaign = gateway.post(
            "/api/v1/campaigns",
            json={"title": "Leitmotif Vault", "setting": "Underdark"},
            headers=auth_headers("soundscape-tester"),
        )
        assert campaign.status_code == 201, campaign.text
        session = gateway.post(
            f"/api/v1/campaigns/{campaign.json()['id']}/sessions",
            json={"title": "Echoing Depths"},
            headers=auth_headers("soundscape-tester"),
        )
        assert session.status_code == 201, session.text
        yield session.json()["id"]


def setup_leitmotif_profile(
    client: TestClient,
    session_id: str,
    character_id: str,
    character_name: str,
    timbre: str,
    tempo: float = 1.0,
    volume: float = 1.0,
) -> None:
    """Register character leitmotif audio signature via public REST frontdoor."""
    res = client.post(
        "/api/v1/soundscape/leitmotif/profile",
        json={
            "session_id": session_id,
            "character_id": character_id,
            "character_name": character_name,
            "instrument_timbre": timbre,
            "tempo_multiplier": tempo,
            "volume_gain": volume,
        },
    )
    assert res.status_code == 200, res.text
