"""Blackbox tests: the gateway forwards stand-in guardrail writes to character_sheet unchanged.

The gateway keeps no policy model. character_sheet validates the body, so a bad policy answers
with the owner's 422 through the gateway. Each test drives the public gateway routes, and
character_sheet runs as a live loopback upstream (ADR-0015).
"""

from fastapi.testclient import TestClient
from gateway_api.main import app


def _auth(issuer, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


def _create_character(client: TestClient, headers: dict[str, str]) -> str:
    res = client.post(
        "/api/v1/characters",
        json={"name": "Warden", "characterClass": "Fighter"},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_unknown_risk_threshold_is_refused_by_the_owner(
    trusted_ws_issuer, character_sheet_upstream, game_session_upstream
):
    """A risk_threshold outside the allowed set answers 422 from character_sheet, not 200."""
    headers = _auth(trusted_ws_issuer, "user_guardrail_owner")
    with TestClient(app) as client:
        char_id = _create_character(client, headers)
        res = client.put(
            f"/api/v1/characters/{char_id}/guardrails",
            json={"risk_threshold": "fearless"},
            headers=headers,
        )
        stored = client.get(f"/api/v1/characters/{char_id}/guardrails", headers=headers)

    assert res.status_code == 422
    assert "risk_threshold" in res.text
    assert stored.status_code == 200
    assert stored.json()["risk_threshold"] == "cautious"


def test_camel_case_policy_fields_are_refused_by_the_owner(
    trusted_ws_issuer, character_sheet_upstream, game_session_upstream
):
    """The gateway accepts one spelling only. A camelCase policy field answers 422 and stores nothing."""
    headers = _auth(trusted_ws_issuer, "user_guardrail_casing")
    with TestClient(app) as client:
        char_id = _create_character(client, headers)
        res = client.put(
            f"/api/v1/characters/{char_id}/guardrails",
            json={"riskThreshold": "balanced"},
            headers=headers,
        )

    assert res.status_code == 422


def test_valid_policy_is_stored_and_returned_by_the_owner(
    trusted_ws_issuer, character_sheet_upstream, game_session_upstream
):
    """A valid policy answers 200 with the owner's stored state, and a read returns it."""
    headers = _auth(trusted_ws_issuer, "user_guardrail_valid")
    policy = {"risk_threshold": "balanced", "avoid_melee": False, "protect_allies": ["Ilka"]}
    with TestClient(app) as client:
        char_id = _create_character(client, headers)
        res = client.put(f"/api/v1/characters/{char_id}/guardrails", json=policy, headers=headers)
        read = client.get(f"/api/v1/characters/{char_id}/guardrails", headers=headers)

    assert res.status_code == 200, res.text
    assert res.json()["stand_in_guardrails"]["risk_threshold"] == "balanced"
    assert read.status_code == 200
    assert read.json()["risk_threshold"] == "balanced"
    assert read.json()["protect_allies"] == ["Ilka"]
