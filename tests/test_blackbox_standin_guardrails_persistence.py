"""Blackbox TDD Integration Tests: Stand-In Guardrails Persistence, Hot-Swap Takeover, and User Profile.

TASK-0357: Stand-In Guardrails Persistence, Absentee Directives & User Profile Management
Governing ADRs: ADR-0003, ADR-0004, ADR-0008, ADR-0013
Hard Invariants:
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with frontdoor setup
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.zitadel_auth import auth_environment, create_signed_token

__all__ = ["auth_environment"]


@pytest.mark.asyncio
async def test_blackbox_put_guardrails_persistence_frontdoor(
    trusted_ws_issuer, character_sheet_upstream, game_session_upstream
):
    """PUT /api/v1/characters/{id}/guardrails updates guardrails and persists across subsequent queries."""
    user_id = "user-valeros"
    headers = {"Authorization": f"Bearer {trusted_ws_issuer.mint(user_id)}"}

    with TestClient(gateway_app) as client:
        created = client.post(
            "/api/v1/characters",
            json={"name": "Valeros", "characterClass": "Fighter", "maxHp": 38},
            headers=headers,
        )
        assert created.status_code == 201, created.text
        char_id = created.json()["id"]

        update_payload = {
            "preserve_spell_slots": {"3": 2},
            "protect_allies": ["Seoni", "Merisiel"],
            "protect_ally_hp_threshold": 0.35,
            "risk_threshold": "cautious",
            "avoid_melee": True,
            "permadeath_safeguard": True,
            "custom_priorities": [
                "Prioritize healing Seoni under 35% HP",
                "Reserve Level 3 spell slot for Revivify",
            ],
        }

        # 1. Update guardrails via public PUT frontdoor
        put_res = client.put(
            f"/api/v1/characters/{char_id}/guardrails",
            json=update_payload,
            headers=headers,
        )
        assert put_res.status_code == 200, f"PUT failed: {put_res.text}"
        put_data = put_res.json()
        assert put_data["id"] == char_id
        assert put_data["stand_in_guardrails"]["risk_threshold"] == "cautious"
        assert put_data["stand_in_guardrails"]["protect_allies"] == ["Seoni", "Merisiel"]
        assert put_data["stand_in_guardrails"]["permadeath_safeguard"] is True
        assert put_data["standInGuardrails"]["risk_threshold"] == "cautious"

        # 2. Verify subsequent GET /api/v1/characters/{id} returns persisted guardrails
        get_res = client.get(f"/api/v1/characters/{char_id}", headers=headers)
        assert get_res.status_code == 200
        get_data = get_res.json()
        assert get_data["stand_in_guardrails"]["risk_threshold"] == "cautious"
        assert get_data["stand_in_guardrails"]["protect_allies"] == ["Seoni", "Merisiel"]
        assert get_data["standInGuardrails"]["protect_allies"] == ["Seoni", "Merisiel"]

        # 3. Verify dedicated GET /api/v1/characters/{id}/guardrails endpoint
        get_gr_res = client.get(f"/api/v1/characters/{char_id}/guardrails", headers=headers)
        assert get_gr_res.status_code == 200
        gr_data = get_gr_res.json()
        assert gr_data["risk_threshold"] == "cautious"
        assert gr_data["protect_allies"] == ["Seoni", "Merisiel"]


@pytest.mark.asyncio
async def test_blackbox_profile_patch_and_get_persistence_frontdoor(auth_environment):
    """PATCH /api/v1/profile updates profile and GET /api/v1/profile returns updated claims."""
    client = auth_environment["client"]
    valid_key = auth_environment["valid_key"]
    kid = auth_environment["kid"]
    user_id = "user-valeros"
    token = create_signed_token(
        valid_key, sub=user_id, kid=kid, roles=["player"], preferred_username="Valeros"
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Initial profile check
    initial_res = client.get("/api/v1/profile", headers=headers)
    assert initial_res.status_code == 200
    initial_data = initial_res.json()
    assert initial_data["user_id"] == user_id

    # Update profile claims via PATCH frontdoor
    patch_payload = {
        "displayName": "Valeros the Undaunted",
        "avatarUrl": "/assets/portraits/valeros-veteran.svg",
        "bio": "Veteran champion of Korvosa, sword for hire, and tavern connoisseur.",
    }

    patch_res = client.patch(
        "/api/v1/profile",
        json=patch_payload,
        headers=headers,
    )
    assert patch_res.status_code == 200, f"PATCH failed: {patch_res.text}"
    patch_data = patch_res.json()
    assert patch_data["display_name"] == "Valeros the Undaunted"
    assert patch_data["avatar_url"] == "/assets/portraits/valeros-veteran.svg"
    assert patch_data["bio"] == patch_payload["bio"]

    # Verify subsequent GET /api/v1/profile reflects the updated values
    get_res = client.get("/api/v1/profile", headers=headers)
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["display_name"] == "Valeros the Undaunted"
    assert get_data["avatar_url"] == "/assets/portraits/valeros-veteran.svg"
    assert get_data["bio"] == patch_payload["bio"]
