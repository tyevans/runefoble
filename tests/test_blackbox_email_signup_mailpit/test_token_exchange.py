"""Blackbox tests for OAuth2 password token grant, refresh tokens, and logout."""

import base64
import json

from fastapi.testclient import TestClient


def test_password_token_grant(client: TestClient) -> None:
    """Verify /api/v1/auth/token exchanges credentials for JWT with proper roles."""
    dm_res = client.post(
        "/api/v1/auth/token",
        json={"username": "DungeonMaster", "password": "Password123!"},
    )
    assert dm_res.status_code == 200
    dm_data = dm_res.json()
    assert "access_token" in dm_data
    assert "refresh_token" in dm_data
    assert "dm" in dm_data["roles"]
    assert "player" in dm_data["roles"]

    player_res = client.post(
        "/api/v1/auth/token",
        json={"username": "AdventurerBob", "password": "Password123!"},
    )
    assert player_res.status_code == 200
    player_data = player_res.json()
    assert "access_token" in player_data
    assert player_data["roles"] == ["player"]


def test_refresh_token_flow(client: TestClient) -> None:
    """Verify /api/v1/auth/refresh issues a new access token from a refresh token."""
    login_res = client.post(
        "/api/v1/auth/token",
        json={"username": "RangerDan", "password": "Password123!"},
    )
    assert login_res.status_code == 200
    refresh_token = login_res.json()["refresh_token"]

    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    refreshed_data = refresh_res.json()
    assert "access_token" in refreshed_data
    assert "refresh_token" in refreshed_data
    assert refreshed_data["token_type"] == "Bearer"


def test_refresh_token_missing_error(client: TestClient) -> None:
    """Verify /api/v1/auth/refresh rejects missing or empty refresh tokens."""
    empty_res = client.post("/api/v1/auth/refresh", json={"refresh_token": ""})
    assert empty_res.status_code == 400
    assert "Missing refresh token" in empty_res.json()["detail"]


def test_logout_flow(client: TestClient) -> None:
    """Verify /api/v1/auth/logout invalidates session and returns success."""
    logout_res = client.post("/api/v1/auth/logout")
    assert logout_res.status_code == 200
    assert logout_res.json()["status"] == "logged_out"


def test_token_structure_and_claims(client: TestClient) -> None:
    """Verify issued JWT contains expected RFC-7519 claims and structure."""
    token_res = client.post(
        "/api/v1/auth/token",
        json={"username": "ElenaArchmage", "password": "Password123!"},
    )
    assert token_res.status_code == 200
    raw_jwt = token_res.json()["access_token"]
    parts = raw_jwt.split(".")
    assert len(parts) == 3

    payload_padded = parts[1] + "=" * (-len(parts[1]) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_padded.encode()).decode())
    assert payload["sub"] == "user-elenaarchmage"
    assert payload["preferred_username"] == "ElenaArchmage"
    assert payload["email"] == "elenaarchmage@runefoble.local"
    assert "roles" in payload
