"""Shared fixtures and harness for Soundscape UI blackbox test suite (TASK-0154).

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0008: Property and Mutation Testing with Hypothesis
- Hard Invariant 1: SpiceDB Zanzibar object authorization
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from soundscape.main import app as soundscape_app

from tests.helpers.ws_identity import bearer

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def client() -> TestClient:
    return TestClient(soundscape_app, headers=bearer("soundscape-tester"))


@pytest.fixture
def gateway_client() -> TestClient:
    return TestClient(gateway_app)


@pytest.fixture
def sample_stem_volumes() -> dict[str, float]:
    return {
        "melody": 0.95,
        "percussion": 0.60,
        "drone": 0.40,
        "ambient": 0.85,
    }


@pytest.fixture
def soundscape_session_id(trusted_ws_issuer, game_session_upstream) -> Iterator[str]:
    """Create a campaign and a session through the gateway frontdoor. The default subject owns both.

    The gateway proxies to the live game_session upstream, so the client enters the gateway lifespan.
    """
    with TestClient(gateway_app) as gateway:
        campaign = gateway.post(
            "/api/v1/campaigns",
            json={"title": "Soundscape Vault", "setting": "Underdark"},
            headers=bearer("soundscape-tester"),
        )
        assert campaign.status_code == 201, campaign.text
        session = gateway.post(
            f"/api/v1/campaigns/{campaign.json()['id']}/sessions",
            json={"title": "Echoing Depths"},
            headers=bearer("soundscape-tester"),
        )
        assert session.status_code == 201, session.text
        yield session.json()["id"]


@pytest.fixture
def sample_foley_cue(soundscape_session_id: str) -> dict[str, Any]:
    return {
        "session_id": soundscape_session_id,
        "cue_name": "thunder",
        "cue_type": "foley",
        "volume_gain": 1.1,
        "duck_music": True,
    }


@pytest.fixture
def sample_tension_payload(soundscape_session_id: str) -> dict[str, Any]:
    return {
        "session_id": soundscape_session_id,
        "combat_active": True,
        "combat_round": 2,
        "enemy_cr_balance": 2.5,
        "lowest_party_health_ratio": 0.4,
    }
