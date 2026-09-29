"""Blackbox frontdoor tests for Dynamic Campaign Sessions Scoping, Scheduling & Offline Cache.

TASK-0354: Dynamic Campaign Sessions Scoping, Scheduling & Offline Cache.
Governing ADRs: ADR-0001 (SpiceDB Zanzibar), ADR-0004 (Lit Web Components),
ADR-0007 (Gateway API & DDD), ADR-0013 (Frontend Microfrontends).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client
from gateway_api.campaign_store import campaign_store
from gateway_api.main import app as gateway_app

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
APP_DATA_SERVICE_TS = FRONTEND_DIR / "src" / "services" / "app-data-service.ts"
FIXTURES_TS = FRONTEND_DIR / "src" / "services" / "app-data-service.fixtures.ts"
SESSION_MODAL_TS = FRONTEND_DIR / "src" / "components" / "runefoble-session-modal.ts"
CAMPAIGN_STORE_PY = REPO_ROOT / "gateway/api/src/gateway_api/campaign_store/store.py"
ROUTERS_CAMPAIGNS_PY = REPO_ROOT / "gateway/api/src/gateway_api/routers/campaigns.py"
TS_TEST_FILE = FRONTEND_DIR / "test" / "campaign-sessions-scoping.test.ts"


@pytest.fixture
def client() -> TestClient:
    return TestClient(gateway_app)


@pytest.fixture(autouse=True)
def reset_stores():
    campaign_store.reset()
    yield
    campaign_store.reset()


def test_file_length_invariants():
    """Verify Hard Invariant 6: All modified source files strictly satisfy line limits (<500 lines)."""
    files_to_check = [
        (APP_DATA_SERVICE_TS, 220),
        (FIXTURES_TS, 160),
        (SESSION_MODAL_TS, 180),
        (CAMPAIGN_STORE_PY, 160),
        (ROUTERS_CAMPAIGNS_PY, 500),
        (Path(__file__), 500),
    ]
    for file_path, max_lines in files_to_check:
        assert file_path.is_file(), f"{file_path} must exist"
        lines = len(file_path.read_text(encoding="utf-8").splitlines())
        assert lines < max_lines, (
            f"{file_path.name} has {lines} lines, exceeding the limit of {max_lines}"
        )


@pytest.mark.asyncio
async def test_backend_create_campaign_seeds_initial_staging_lobby_with_spicedb(client: TestClient):
    """Verify POST /api/v1/campaigns automatically seeds an initial staging lobby session with SpiceDB auth."""
    headers_owner = {"X-User-Id": "dm_evelyn"}
    spicedb = get_spicedb_client()

    res_camp = client.post(
        "/api/v1/campaigns",
        json={"title": "Rime of the Frostmaiden", "setting": "Icewind Dale"},
        headers=headers_owner,
    )
    assert res_camp.status_code == 201
    camp_data = res_camp.json()
    campaign_id = camp_data["id"]

    # 1. Verify owner can query campaign sessions frontdoor -> contains initial seeded session
    res_sessions = client.get(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        headers=headers_owner,
    )
    assert res_sessions.status_code == 200
    sessions = res_sessions.json()
    assert len(sessions) == 1
    seeded = sessions[0]
    assert seeded["title"] == "Session #1: Staging Lobby"
    assert seeded["status"] == "lobby"
    assert seeded["campaign_id"] == campaign_id
    assert seeded["round"] == 1
    assert seeded["participants_count"] == 0
    assert "Session #15: Chamber of Horrors" not in [s["title"] for s in sessions]

    # 2. Verify SpiceDB Zanzibar permissions on the seeded session
    session_id = seeded["id"]
    # Owner has control permission on both session and game_session
    assert await spicedb.check_permission("session", session_id, "control", "user", "dm_evelyn")
    assert await spicedb.check_permission(
        "game_session", session_id, "control", "user", "dm_evelyn"
    )
    assert await spicedb.check_permission("session", session_id, "observe", "user", "dm_evelyn")

    # 3. Add player via invite and verify player permissions on seeded session
    res_inv = client.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json={"role": "player"},
        headers=headers_owner,
    )
    token = res_inv.json()["token"]

    headers_player = {"X-User-Id": "player_drizzt"}
    res_join = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": token},
        headers=headers_player,
    )
    assert res_join.status_code == 200

    # Player has participate & observe, but lacks control
    assert await spicedb.check_permission(
        "session", session_id, "participate", "user", "player_drizzt"
    )
    assert await spicedb.check_permission("session", session_id, "observe", "user", "player_drizzt")
    assert not await spicedb.check_permission(
        "session", session_id, "control", "user", "player_drizzt"
    )


@pytest.mark.asyncio
async def test_campaign_sessions_isolation_and_offline_scoping(client: TestClient):
    """Verify multi-campaign session roster isolation and persistence across listings."""
    headers_a = {"X-User-Id": "owner_alpha"}
    headers_b = {"X-User-Id": "owner_beta"}

    # 1. Create Campaign A and schedule Session 2
    res_a = client.post(
        "/api/v1/campaigns",
        json={"title": "Netheril Ruins"},
        headers=headers_a,
    )
    camp_a = res_a.json()["id"]

    res_sess_a = client.post(
        f"/api/v1/campaigns/{camp_a}/sessions",
        json={
            "title": "Session #2: The Floating Conclave",
            "status": "upcoming",
            "scheduled_at": "2026-11-15T19:00:00Z",
            "description": "Exploration of the ancient fallen city.",
        },
        headers=headers_a,
    )
    assert res_sess_a.status_code == 201

    # 2. Create Campaign B
    res_b = client.post(
        "/api/v1/campaigns",
        json={"title": "Underdark Expeditions"},
        headers=headers_b,
    )
    camp_b = res_b.json()["id"]

    # 3. Query Campaign A sessions -> sees seeded lobby + Session 2
    sessions_a = client.get(f"/api/v1/campaigns/{camp_a}/sessions", headers=headers_a).json()
    assert len(sessions_a) == 2
    titles_a = [s["title"] for s in sessions_a]
    assert "Session #1: Staging Lobby" in titles_a
    assert "Session #2: The Floating Conclave" in titles_a
    assert "Session #15: Chamber of Horrors" not in titles_a

    # 4. Query Campaign B sessions -> sees only its own seeded lobby
    sessions_b = client.get(f"/api/v1/campaigns/{camp_b}/sessions", headers=headers_b).json()
    assert len(sessions_b) == 1
    titles_b = [s["title"] for s in sessions_b]
    assert "Session #1: Staging Lobby" in titles_b
    assert "Session #2: The Floating Conclave" not in titles_b
    assert "Session #15: Chamber of Horrors" not in titles_b

    # 5. Cross-campaign boundary protection: owner_b cannot read or modify campaign A sessions
    res_unauth = client.get(f"/api/v1/campaigns/{camp_a}/sessions", headers=headers_b)
    assert res_unauth.status_code == 403


def test_frontend_node_unit_suite_execution():
    """Execute Node test runner on frontend/test/campaign-sessions-scoping.test.ts."""
    assert TS_TEST_FILE.is_file()
    result = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "--test",
            str(TS_TEST_FILE.relative_to(REPO_ROOT)),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Frontend sessions scoping tests failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "fail 0" in result.stdout
