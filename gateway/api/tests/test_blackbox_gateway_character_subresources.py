"""Blackbox tests: gateway character subresource routes proxy to character_sheet (TASK-0586).

Each test drives the public gateway routes. character_sheet runs as a live loopback upstream.
The gateway answers with the owner's status and body. It never answers from memory, so an
owner error reaches the caller and an unreachable owner returns 503 (ADR-0015 b).
"""

from fastapi.testclient import TestClient
from gateway_api.main import app


def _auth(issuer, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


def _create_character(client: TestClient, headers: dict[str, str], max_hp: int = 20) -> str:
    res = client.post(
        "/api/v1/characters",
        json={"name": "Subresource", "characterClass": "Fighter", "maxHp": max_hp},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_health_change_is_visible_on_the_next_read(
    trusted_ws_issuer, character_sheet_upstream, game_session_upstream
):
    """Damage posted through the gateway lowers the HP that a later GET returns."""
    headers = _auth(trusted_ws_issuer, "user_health")
    with TestClient(app) as client:
        char_id = _create_character(client, headers, max_hp=20)
        changed = client.post(
            f"/api/v1/characters/{char_id}/health",
            json={"delta": -5, "source": "damage"},
            headers=headers,
        )
        read = client.get(f"/api/v1/characters/{char_id}", headers=headers)

    assert changed.status_code == 200, changed.text
    assert read.status_code == 200
    assert read.json()["currentHp"] == 15


def test_unknown_character_is_refused_with_403(
    trusted_ws_issuer, character_sheet_upstream, game_session_upstream
):
    """A subresource call on a character the caller holds no relation to is refused with 403.

    The owner denies before the handler runs, and the gateway passes that 403 through. It does not answer 200.
    """
    headers = _auth(trusted_ws_issuer, "user_unknown")
    missing = "00000000-0000-4000-8000-0000000000ff"
    with TestClient(app) as client:
        res = client.post(
            f"/api/v1/characters/{missing}/health",
            json={"delta": -1, "source": "damage"},
            headers=headers,
        )

    assert res.status_code == 403


def test_owner_validation_error_passes_through_unchanged(
    trusted_ws_issuer, character_sheet_upstream, game_session_upstream
):
    """A policy that character_sheet rejects answers 422 with the owner's error body."""
    headers = _auth(trusted_ws_issuer, "user_validation")
    with TestClient(app) as client:
        char_id = _create_character(client, headers)
        res = client.put(
            f"/api/v1/characters/{char_id}/guardrails",
            json={"risk_threshold": "fearless"},
            headers=headers,
        )

    assert res.status_code == 422
    assert "risk_threshold" in res.text


def test_owner_down_returns_503_on_a_subresource(
    trusted_ws_issuer, character_sheet_upstream, game_session_upstream, monkeypatch
):
    """With character_sheet unreachable, a subresource call fails with 503 and no fallback body.

    The character is created while the owner is up. The gateway then restarts against a closed
    port, so the call reaches a permitted character and fails at the owner.
    """
    headers = _auth(trusted_ws_issuer, "user_owner_down")
    with TestClient(app) as client:
        char_id = _create_character(client, headers)

    monkeypatch.setenv("RUNEFOBLE_CHARACTER_SHEET_URL", "http://127.0.0.1:9")
    with TestClient(app) as client:
        res = client.post(
            f"/api/v1/characters/{char_id}/health",
            json={"delta": -3, "source": "damage"},
            headers=headers,
        )

    assert res.status_code == 503
    assert res.json()["upstream"] == "character_sheet"


def test_guardrails_put_then_get_returns_the_stored_policy(
    trusted_ws_issuer, character_sheet_upstream, game_session_upstream
):
    """A guardrail policy written through the gateway is the one a later GET returns."""
    headers = _auth(trusted_ws_issuer, "user_guardrail_roundtrip")
    policy = {"risk_threshold": "balanced", "avoid_melee": True, "protect_allies": ["Ilka"]}
    with TestClient(app) as client:
        char_id = _create_character(client, headers)
        put = client.put(f"/api/v1/characters/{char_id}/guardrails", json=policy, headers=headers)
        read = client.get(f"/api/v1/characters/{char_id}/guardrails", headers=headers)

    assert put.status_code == 200, put.text
    assert read.status_code == 200
    assert read.json()["risk_threshold"] == "balanced"
    assert read.json()["avoid_melee"] is True
    assert read.json()["protect_allies"] == ["Ilka"]


def test_inventory_add_and_remove_map_to_the_owner_routes(
    trusted_ws_issuer, character_sheet_upstream, game_session_upstream
):
    """Adding an item and deleting it through the gateway reaches the owner's inventory routes."""
    headers = _auth(trusted_ws_issuer, "user_inventory")
    with TestClient(app) as client:
        char_id = _create_character(client, headers)
        added = client.post(
            f"/api/v1/characters/{char_id}/inventory",
            json={"itemId": "rope-50ft", "name": "Rope", "quantity": 2},
            headers=headers,
        )
        removed = client.delete(
            f"/api/v1/characters/{char_id}/inventory/rope-50ft",
            params={"quantity": 2},
            headers=headers,
        )

    assert added.status_code == 200, added.text
    assert "rope-50ft" in str(added.json()["inventory"])
    assert removed.status_code == 200, removed.text
    assert "rope-50ft" not in str(removed.json()["inventory"])


def test_condition_apply_and_remove_map_to_the_owner_routes(
    trusted_ws_issuer, character_sheet_upstream, game_session_upstream
):
    """A condition applied through the gateway is cleared by a DELETE through the gateway."""
    headers = _auth(trusted_ws_issuer, "user_condition")
    with TestClient(app) as client:
        char_id = _create_character(client, headers)
        applied = client.post(
            f"/api/v1/characters/{char_id}/conditions",
            json={"condition": "prone", "durationRounds": 2},
            headers=headers,
        )
        cleared = client.delete(
            f"/api/v1/characters/{char_id}/conditions/prone",
            headers=headers,
        )

    assert applied.status_code == 200, applied.text
    assert "prone" in str(applied.json()["conditions"])
    assert cleared.status_code == 200, cleared.text
    assert "prone" not in str(cleared.json()["conditions"])
