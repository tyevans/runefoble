"""Blackbox frontdoor tests for fail-closed authorization in Campaign Analytics and Soundscape (TASK-0557).

Governed by:
- ADR-0001: SpiceDB Zanzibar object authorization (schema permissions only)
- ADR-0007: Campaign analytics and soundscape bounded contexts own their read and control routes
- ADR-0014: Behaviour-driven frontdoor tests
- ADR-0015: Verified bearer tokens; membership comes from invites
- Hard Invariant 1: No role checks in business logic
- Hard Invariant 7: Blackbox TDD with frontdoor setup

Setup runs through the gateway frontdoors (campaign create, invite, join). Assertions read public
HTTP responses only. The outage test replaces the SpiceDB check at the process boundary.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from runefoble_auth.errors import AuthzUnavailableError
from runefoble_auth.spicedb import MockSpiceDBClient
from soundscape.main import app as soundscape_app

from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

DM = "dm_evelyn"
PLAYER = "player_valeros"
STRANGER = "stranger_bob"


def _bearer(sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def gateway(game_session_upstream) -> Iterator[TestClient]:
    """Gateway lifespan entered after game_session is served, so campaign routes proxy."""
    with TestClient(gateway_app) as client:
        yield client


@pytest.fixture
def soundscape() -> TestClient:
    """Soundscape service with no default headers. Each test sends the caller's token."""
    return TestClient(soundscape_app)


@pytest.fixture
def campaign(gateway: TestClient) -> dict[str, str]:
    """The DM creates a campaign. The player joins through an invite. Return ids for the routes."""
    created = gateway.post(
        "/api/v1/campaigns",
        json={"title": "Authz Vault", "setting": "Underdark"},
        headers=_bearer(DM),
    )
    assert created.status_code == 201, created.text
    cid = created.json()["id"]

    sessions = gateway.get(f"/api/v1/campaigns/{cid}/sessions", headers=_bearer(DM))
    assert sessions.status_code == 200, sessions.text
    sid = sessions.json()[0]["id"]

    invite = gateway.post(
        f"/api/v1/campaigns/{cid}/invites", json={"role": "player"}, headers=_bearer(DM)
    )
    assert invite.status_code == 201, invite.text
    joined = gateway.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite.json()["token"]},
        headers=_bearer(PLAYER),
    )
    assert joined.status_code == 200, joined.text
    return {"cid": cid, "sid": sid}


def _duck_body(session_id: str) -> dict[str, Any]:
    return {"session_id": session_id, "is_ducked": True, "reason": "speech"}


def _stems_body(session_id: str) -> dict[str, Any]:
    return {"session_id": session_id, "stem_volumes": {"melody": 0.5}}


def _tension_body(session_id: str) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "combat_active": True,
        "combat_round": 2,
        "enemy_cr_balance": 2.0,
        "lowest_party_health_ratio": 0.5,
    }


def _mood_body(session_id: str) -> dict[str, Any]:
    return {"session_id": session_id, "mood": "boss", "master_volume": 0.8}


# ---------------------------------------------------------------------------
# Campaign Analytics through the gateway
# ---------------------------------------------------------------------------


def test_analytics_gateway_call_without_principal_is_unauthorized(
    gateway: TestClient, campaign: dict[str, str]
) -> None:
    """A call with no bearer token gets 401. The gateway no longer forwards an anonymous read."""
    cid = campaign["cid"]
    res = gateway.get(f"/api/v1/analytics/campaigns/{cid}/heatmap")
    assert res.status_code == 401


def test_analytics_gateway_call_by_stranger_is_forbidden(
    gateway: TestClient, campaign: dict[str, str]
) -> None:
    """A verified caller with no campaign relation gets 403 on an analytics read."""
    cid = campaign["cid"]
    res = gateway.get(f"/api/v1/analytics/campaigns/{cid}/heatmap", headers=_bearer(STRANGER))
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# Soundscape controls: verified principal and schema permission
# ---------------------------------------------------------------------------


def test_soundscape_duck_without_principal_is_unauthorized(
    soundscape: TestClient, campaign: dict[str, str]
) -> None:
    res = soundscape.post("/api/v1/soundscape/duck", json=_duck_body(campaign["sid"]))
    assert res.status_code == 401


def test_soundscape_duck_allows_dm_and_denies_player(
    soundscape: TestClient, campaign: dict[str, str]
) -> None:
    body = _duck_body(campaign["sid"])
    player = soundscape.post("/api/v1/soundscape/duck", headers=_bearer(PLAYER), json=body)
    assert player.status_code == 403
    assert "Forbidden" in player.json()["detail"]

    dm = soundscape.post("/api/v1/soundscape/duck", headers=_bearer(DM), json=body)
    assert dm.status_code == 200
    assert dm.json()["is_ducked"] is True


def test_soundscape_stem_volume_denies_player_and_allows_dm(
    soundscape: TestClient, campaign: dict[str, str]
) -> None:
    body = _stems_body(campaign["sid"])
    player = soundscape.post("/api/v1/soundscape/stems/volume", headers=_bearer(PLAYER), json=body)
    assert player.status_code == 403

    dm = soundscape.post("/api/v1/soundscape/stems/volume", headers=_bearer(DM), json=body)
    assert dm.status_code == 200
    assert dm.json()["stem_channels"]["melody"] == 0.5


def test_soundscape_tension_calculate_without_principal_is_unauthorized(
    soundscape: TestClient, campaign: dict[str, str]
) -> None:
    res = soundscape.post(
        "/api/v1/soundscape/tension/calculate", json=_tension_body(campaign["sid"])
    )
    assert res.status_code == 401


def test_soundscape_tension_calculate_denies_player_and_allows_dm(
    soundscape: TestClient, campaign: dict[str, str]
) -> None:
    body = _tension_body(campaign["sid"])
    player = soundscape.post(
        "/api/v1/soundscape/tension/calculate", headers=_bearer(PLAYER), json=body
    )
    assert player.status_code == 403

    dm = soundscape.post("/api/v1/soundscape/tension/calculate", headers=_bearer(DM), json=body)
    assert dm.status_code == 200
    assert dm.json()["tension_score"] > 50


def test_soundscape_mood_override_denies_player_and_allows_dm(
    soundscape: TestClient, campaign: dict[str, str]
) -> None:
    body = _mood_body(campaign["sid"])
    player = soundscape.post("/api/v1/soundscape/override", headers=_bearer(PLAYER), json=body)
    assert player.status_code == 403

    dm = soundscape.post("/api/v1/soundscape/override", headers=_bearer(DM), json=body)
    assert dm.status_code == 200
    assert dm.json()["manual_override"] is True


def test_soundscape_mood_override_without_principal_is_unauthorized(
    soundscape: TestClient, campaign: dict[str, str]
) -> None:
    res = soundscape.post("/api/v1/soundscape/override", json=_mood_body(campaign["sid"]))
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Fail-closed: a SpiceDB outage is a 503, never a denial or an allow
# ---------------------------------------------------------------------------


def test_soundscape_spicedb_outage_returns_503(
    soundscape: TestClient,
    campaign: dict[str, str],
    default_spicedb_client: MockSpiceDBClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With SpiceDB unreachable, the DM's duck request fails with 503 and changes nothing."""

    async def unreachable(*_args: Any, **_kwargs: Any) -> bool:
        raise AuthzUnavailableError("SpiceDB did not answer")

    monkeypatch.setattr(default_spicedb_client, "check_permission", unreachable)

    res = soundscape.post(
        "/api/v1/soundscape/duck", headers=_bearer(DM), json=_duck_body(campaign["sid"])
    )
    assert res.status_code == 503
    assert res.json() == {"error": "authorization_unavailable"}
