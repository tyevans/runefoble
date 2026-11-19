"""Blackbox tests for TASK-0689: receivers accept a user bearer or the service credential (ADR-0015 c, e).

Requests use only public HTTP routes and subprocess start-up. The service credential
grants the routes that the MCP gateway calls. It never grants a user-scoped route, and a
user bearer that fails verification is refused even when the credential is present.
"""

from __future__ import annotations

import os
import subprocess
from uuid import uuid4

import pytest
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient
from game_session.main import app as session_app
from runefoble_platform.service_credential import SERVICE_CREDENTIAL_HEADER

from tests.helpers.process import run_python_child
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

CREDENTIAL = os.environ["RUNEFOBLE_SERVICE_CREDENTIAL"]
SERVICE_ONLY = {SERVICE_CREDENTIAL_HEADER: CREDENTIAL}


def _owner_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint('credential-owner')}"}


def _create_character(client: TestClient) -> str:
    res = client.post(
        "/api/v1/characters",
        json={"name": "Kyra", "character_class": "Cleric", "max_hp": 30},
        headers=_owner_headers(),
    )
    assert res.status_code == 200, res.text
    return str(res.json()["character_id"])


def _create_session(client: TestClient) -> str:
    """Create a campaign as the owner, then a session. The owner holds run_session on it."""
    campaign = client.post(
        "/api/v1/campaigns",
        json={"title": "Credential Campaign", "setting": "Sword Coast"},
        headers=_owner_headers(),
    )
    assert campaign.status_code == 201, campaign.text
    created = client.post(
        f"/api/v1/campaigns/{campaign.json()['id']}/sessions",
        json={"title": "Credential Test"},
        headers=_owner_headers(),
    )
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


def test_character_read_refuses_the_service_credential_without_a_user():
    """A sheet read needs a user who holds `character.view` (ADR-0001, ADR-0015 e)."""
    client = TestClient(character_app)
    character_id = _create_character(client)

    res = client.get(f"/api/v1/characters/{character_id}", headers=SERVICE_ONLY)

    assert res.status_code == 401


def test_character_read_refuses_a_call_with_no_credential_and_no_bearer():
    client = TestClient(character_app)
    character_id = _create_character(client)

    res = client.get(f"/api/v1/characters/{character_id}")

    assert res.status_code == 401


def test_character_read_refuses_a_wrong_service_credential():
    client = TestClient(character_app)
    character_id = _create_character(client)

    res = client.get(
        f"/api/v1/characters/{character_id}",
        headers={SERVICE_CREDENTIAL_HEADER: "not-the-credential"},
    )

    assert res.status_code == 401


def test_service_credential_cannot_create_a_user_owned_character():
    """Creating a character writes an owner relation, so it needs a verified user."""
    client = TestClient(character_app)

    res = client.post(
        "/api/v1/characters",
        json={"name": "Ghost", "character_class": "Rogue", "max_hp": 10},
        headers=SERVICE_ONLY,
    )

    assert res.status_code == 401


def test_invalid_user_bearer_is_refused_even_with_the_service_credential():
    client = TestClient(character_app)
    character_id = _create_character(client)

    res = client.get(
        f"/api/v1/characters/{character_id}",
        headers={**SERVICE_ONLY, "Authorization": "Bearer not-a-real-token"},
    )

    assert res.status_code == 401


def test_game_session_read_accepts_the_service_credential():
    client = TestClient(session_app)
    session_id = _create_session(client)

    res = client.get(f"/api/v1/sessions/{session_id}", headers=SERVICE_ONLY)

    assert res.status_code == 200


def test_game_session_join_refuses_the_service_credential():
    """Joining a session acts for a player, so it needs a verified user."""
    client = TestClient(session_app)
    session_id = _create_session(client)

    res = client.post(
        f"/api/v1/sessions/{session_id}/join",
        json={
            "character_id": str(uuid4()),
            "character_name": "Mallory",
            "character_class": "Rogue",
        },
        headers=SERVICE_ONLY,
    )

    assert res.status_code == 401


def _run_import(
    module: str, env_overrides: dict[str, str | None]
) -> subprocess.CompletedProcess[str]:
    return run_python_child(f"import {module}", env_overrides)


@pytest.mark.parametrize(
    "module",
    [
        "character_sheet.dependencies",
        "game_session.settlement.auth.tokens",
        "board_state.dependencies",
        "rules_compendium.dependencies",
    ],
)
def test_receiver_refuses_to_start_without_service_credential(module):
    result = _run_import(module, {})

    assert result.returncode != 0
    assert "RUNEFOBLE_SERVICE_CREDENTIAL" in result.stderr


def test_receiver_refuses_to_start_with_blank_service_credential():
    result = _run_import("character_sheet.dependencies", {"RUNEFOBLE_SERVICE_CREDENTIAL": "  "})

    assert result.returncode != 0
    assert "RUNEFOBLE_SERVICE_CREDENTIAL" in result.stderr
