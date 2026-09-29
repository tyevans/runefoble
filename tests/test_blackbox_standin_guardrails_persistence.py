"""Blackbox TDD Integration Tests: Stand-In Guardrails Persistence, Hot-Swap Takeover, and User Profile.

TASK-0357: Stand-In Guardrails Persistence, Absentee Directives & User Profile Management
Governing ADRs: ADR-0003, ADR-0004, ADR-0008, ADR-0013
Hard Invariants:
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with frontdoor setup
"""

from __future__ import annotations

from pathlib import Path

import pytest
from gateway_api.auth import get_spicedb_client
from gateway_api.character_store import character_store

from tests.helpers.zitadel_auth import auth_environment, create_signed_token

__all__ = ["auth_environment"]


@pytest.fixture(autouse=True)
def setup_test_character_and_permissions():
    """Ensure Valeros character exists and test user has edit/view relationships."""
    char = character_store.get_character("char-valeros")
    if not char:
        from gateway_api.character_defaults import DEFAULT_CHARACTERS

        valeros_def = next(c for c in DEFAULT_CHARACTERS if c["id"] == "char-valeros")
        char = character_store.create_from_request(
            type("Req", (), valeros_def)(), owner_id="user-valeros"
        )
    return char


@pytest.mark.asyncio
async def test_blackbox_put_guardrails_persistence_frontdoor(auth_environment):
    """PUT /api/v1/characters/{id}/guardrails updates guardrails and persists across subsequent queries."""
    client = auth_environment["client"]
    valid_key = auth_environment["valid_key"]
    kid = auth_environment["kid"]
    user_id = "user-valeros"
    token = create_signed_token(
        valid_key, sub=user_id, kid=kid, roles=["player"], preferred_username="Valeros"
    )
    headers = {"Authorization": f"Bearer {token}"}
    char_id = "char-valeros"

    # Configure SpiceDB Zanzibar permission for test caller
    spicedb = get_spicedb_client()
    await spicedb.write_relationship(
        resource_type="character",
        resource_id=char_id,
        relation="owner",
        subject_type="user",
        subject_id=user_id,
    )

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
async def test_blackbox_hot_swap_session_takeover_frontdoor(auth_environment):
    """POST /api/v1/sessions/{id}/hot-swap hands off active turn control to authenticating player."""
    client = auth_environment["client"]
    valid_key = auth_environment["valid_key"]
    kid = auth_environment["kid"]
    user_id = "user-valeros"
    session_id = "session-tomb-14"
    char_id = "char-valeros"
    token = create_signed_token(
        valid_key, sub=user_id, kid=kid, roles=["player"], preferred_username="Valeros"
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Ensure character is initially flagged as AI stand-in
    char = character_store.get_character(char_id)
    if char:
        char.is_stand_in_active = True

    # Setup Zanzibar permission
    spicedb = get_spicedb_client()
    await spicedb.write_relationship(
        resource_type="character",
        resource_id=char_id,
        relation="owner",
        subject_type="user",
        subject_id=user_id,
    )
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=session_id,
        relation="player",
        subject_type="user",
        subject_id=user_id,
    )

    hot_swap_payload = {
        "playerId": user_id,
        "characterId": char_id,
    }

    res = client.post(
        f"/api/v1/sessions/{session_id}/hot-swap",
        json=hot_swap_payload,
        headers=headers,
    )
    assert res.status_code == 200, f"Hot-swap failed: {res.text}"
    data = res.json()
    assert data["session_id"] == session_id
    assert data["character_id"] == char_id
    assert data["status"] == "control_transferred"
    assert data["is_stand_in_active"] is False

    # Verify character record in store has is_stand_in_active cleared
    assert char.is_stand_in_active is False


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


def test_file_length_invariants():
    """Hard Invariant 6: Ensure all modified backend router files are strictly < 500 lines."""
    base_dir = Path(__file__).resolve().parent.parent
    files_to_check = [
        Path(__file__),
        base_dir / "gateway/api/src/gateway_api/character_models.py",
        base_dir / "gateway/api/src/gateway_api/character_store_mutations.py",
        base_dir / "gateway/api/src/gateway_api/routers/character_subresources.py",
        base_dir / "gateway/api/src/gateway_api/routers/tabletop.py",
        base_dir / "gateway/api/src/gateway_api/routers/auth/profile.py",
    ]
    for file_path in files_to_check:
        assert file_path.exists(), f"File {file_path} does not exist"
        line_count = len(file_path.read_text().splitlines())
        assert line_count < 500, f"{file_path.name} exceeds 500 lines ({line_count} lines)"
