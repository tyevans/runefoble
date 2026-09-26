"""Blackbox TDD frontdoor test suite for live SpiceDB gRPC integration and schema bootstrapper.

Verifies:
1. Frontdoor campaign role assignment (POST /api/v1/campaigns/{id}/roles).
2. Live Zanzibar graph evaluation against running SpiceDB container.
3. Schema migration bootstrapping using runefoble.zed.
4. Seamless fallback to in-memory mock client when disconnected or unreachable.
5. Tuple deletion and immediate permission revocation against live Zanzibar engine.
"""

import shutil
import socket
import subprocess
import time
from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import set_spicedb_client
from gateway_api.main import app
from runefoble_auth.bootstrap_schema import bootstrap_schema
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_spicedb_endpoint() -> Generator[str | None]:
    """Spins up a lightweight isolated in-memory SpiceDB test container if Docker is available."""
    if not shutil.which("docker"):
        yield None
        return

    port = _find_free_port()
    try:
        container_id = (
            subprocess.check_output(
                [
                    "docker",
                    "run",
                    "-d",
                    "--rm",
                    "-p",
                    f"{port}:50051",
                    "authzed/spicedb:v1.34.0",
                    "serve-testing",
                ],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception:
        yield None
        return

    endpoint = f"localhost:{port}"
    # Wait for container gRPC endpoint to become responsive
    deadline = time.time() + 10
    ready = False
    while time.time() < deadline:
        try:
            with socket.create_connection(("localhost", port), timeout=0.5):
                ready = True
                break
        except OSError:
            time.sleep(0.2)

    if not ready:
        subprocess.run(["docker", "kill", container_id], capture_output=True)
        yield None
        return

    # Yield endpoint to test suite
    yield endpoint

    # Teardown container
    subprocess.run(["docker", "kill", container_id], capture_output=True)


@pytest.mark.asyncio
async def test_mock_spicedb_frontdoor_role_assignment():
    """Verify role assignment and enforcement using MockSpiceDBClient."""
    mock_client = MockSpiceDBClient()
    set_spicedb_client(mock_client)
    tc = TestClient(app)

    camp_id = f"camp-mock-{uuid4().hex[:8]}"
    user_alice = f"user-{uuid4().hex[:6]}"
    user_dm = f"dm-{uuid4().hex[:6]}"

    # Unassigned -> 403 Forbidden
    res = tc.get(f"/api/v1/sessions/{camp_id}", headers={"X-User-Id": user_alice})
    assert res.status_code == 403
    assert res.json()["detail"]["required_permission"] == "view"

    # Assign player role via public gateway endpoint
    res_assign = tc.post(
        f"/api/v1/campaigns/{camp_id}/roles",
        json={"user_id": user_alice, "role": "player"},
    )
    assert res_assign.status_code == 200
    assert res_assign.json()["status"] == "role_assigned"

    # Player can now view session
    res_view = tc.get(f"/api/v1/sessions/{camp_id}", headers={"X-User-Id": user_alice})
    assert res_view.status_code == 200
    assert res_view.json()["id"] == camp_id

    # Player cannot advance turn
    res_adv = tc.post(
        f"/api/v1/sessions/{camp_id}/turns/advance",
        headers={"X-User-Id": user_alice},
        json={"next_character_id": "c1"},
    )
    assert res_adv.status_code == 403

    # Assign DM role
    res_assign_dm = tc.post(
        f"/api/v1/campaigns/{camp_id}/roles",
        json={"user_id": user_dm, "role": "dungeon_master"},
    )
    assert res_assign_dm.status_code == 200

    # DM can advance turn
    res_adv_dm = tc.post(
        f"/api/v1/sessions/{camp_id}/turns/advance",
        headers={"X-User-Id": user_dm},
        json={"next_character_id": "c1"},
    )
    assert res_adv_dm.status_code == 200
    assert res_adv_dm.json()["status"] == "turn_advanced"


@pytest.mark.asyncio
async def test_live_spicedb_frontdoor_role_assignment_and_checks(live_spicedb_endpoint: str | None):
    """Verify live SpiceDB gRPC connection with Zanzibar schema and frontdoor endpoints."""
    if not live_spicedb_endpoint:
        pytest.skip("Docker unavailable or SpiceDB container failed to start")

    token = "test_live_secret"
    live_client = SpiceDBClient(
        endpoint=live_spicedb_endpoint,
        token=token,
        use_mock=False,
    )

    # 1. Bootstrap Zanzibar schema against live SpiceDB engine
    schema_text = await bootstrap_schema(client=live_client)
    assert "definition campaign" in schema_text
    assert "relation dungeon_master: user" in schema_text

    # 2. Attach live client to Gateway
    set_spicedb_client(live_client)
    tc = TestClient(app)

    camp_id = f"camp-live-{uuid4().hex[:8]}"
    player_id = "player_talia"
    dm_id = "dm_garrick"

    # 3. Before assignment -> 403 Forbidden
    res_unauth = tc.get(f"/api/v1/sessions/{camp_id}", headers={"X-User-Id": player_id})
    assert res_unauth.status_code == 403

    # 4. Assign player role via Gateway API
    res_role = tc.post(
        f"/api/v1/campaigns/{camp_id}/roles",
        json={"user_id": player_id, "role": "player"},
    )
    assert res_role.status_code == 200
    assert res_role.json()["status"] == "role_assigned"

    # 5. Verify live Zanzibar check via Gateway
    res_player_view = tc.get(f"/api/v1/sessions/{camp_id}", headers={"X-User-Id": player_id})
    assert res_player_view.status_code == 200

    # 6. Player cannot advance turn
    res_player_adv = tc.post(
        f"/api/v1/sessions/{camp_id}/turns/advance",
        headers={"X-User-Id": player_id},
        json={"next_character_id": "char_1"},
    )
    assert res_player_adv.status_code == 403

    # 7. Assign DM role via Gateway API
    res_dm_role = tc.post(
        f"/api/v1/campaigns/{camp_id}/roles",
        json={"user_id": dm_id, "role": "dungeon_master"},
    )
    assert res_dm_role.status_code == 200

    # 8. DM can advance turn
    res_dm_adv = tc.post(
        f"/api/v1/sessions/{camp_id}/turns/advance",
        headers={"X-User-Id": dm_id},
        json={"next_character_id": "char_1"},
    )
    assert res_dm_adv.status_code == 200
    assert res_dm_adv.json()["status"] == "turn_advanced"

    # 9. Verify direct permission check via live SpiceDB client
    assert await live_client.check_permission("campaign", camp_id, "view", "user", player_id)
    assert not await live_client.check_permission(
        "campaign", camp_id, "run_session", "user", player_id
    )
    assert await live_client.check_permission("campaign", camp_id, "run_session", "user", dm_id)


@pytest.mark.asyncio
async def test_live_spicedb_relationship_deletion_and_revocation(
    live_spicedb_endpoint: str | None,
):
    """Verify live tuple deletion instantly revokes permissions in SpiceDB."""
    if not live_spicedb_endpoint:
        pytest.skip("Docker unavailable or SpiceDB container failed to start")

    live_client = SpiceDBClient(
        endpoint=live_spicedb_endpoint,
        token="test_deletion_token",
        use_mock=False,
    )
    await bootstrap_schema(client=live_client)
    set_spicedb_client(live_client)
    tc = TestClient(app)

    camp_id = f"camp-del-{uuid4().hex[:8]}"
    user_id = "user_revoked"

    # Grant player role
    tc.post(
        f"/api/v1/campaigns/{camp_id}/roles",
        json={"user_id": user_id, "role": "player"},
    )

    # Allowed
    res1 = tc.get(f"/api/v1/sessions/{camp_id}", headers={"X-User-Id": user_id})
    assert res1.status_code == 200

    # Delete relationship in live SpiceDB
    await live_client.delete_relationship(
        resource_type="campaign",
        resource_id=camp_id,
        relation="player",
        subject_type="user",
        subject_id=user_id,
    )

    # Immediately denied
    res2 = tc.get(f"/api/v1/sessions/{camp_id}", headers={"X-User-Id": user_id})
    assert res2.status_code == 403


@pytest.mark.asyncio
async def test_spicedb_resilient_fallback_on_unreachable_endpoint():
    """Verify SpiceDBClient falls back gracefully to in-memory mock when endpoint is unreachable."""
    unreachable_client = SpiceDBClient(
        endpoint="localhost:59997",
        token="invalid_token",
        use_mock=False,
    )
    set_spicedb_client(unreachable_client)
    tc = TestClient(app)

    camp_id = f"camp-fallback-{uuid4().hex[:8]}"
    user_id = "user_fallback"

    # Assign role -> handles gRPC connection failure and writes to mock fallback
    res = tc.post(
        f"/api/v1/campaigns/{camp_id}/roles",
        json={"user_id": user_id, "role": "player"},
    )
    assert res.status_code == 200

    # View session -> evaluates against mock fallback
    res_view = tc.get(f"/api/v1/sessions/{camp_id}", headers={"X-User-Id": user_id})
    assert res_view.status_code == 200

    # Read relationships from mock fallback
    rels = await unreachable_client.read_relationships(
        resource_type="campaign", resource_id=camp_id
    )
    assert any(r.subject_id == user_id for r in rels)


@pytest.mark.asyncio
async def test_schema_bootstrapper_execution(live_spicedb_endpoint: str | None):
    """Verify schema bootstrapper applies schema from file and supports dry-run or mock."""
    mock_client = MockSpiceDBClient()
    applied = await bootstrap_schema(client=mock_client)
    assert "definition campaign" in applied
    assert await mock_client.read_schema() == applied

    if live_spicedb_endpoint:
        live_client = SpiceDBClient(
            endpoint=live_spicedb_endpoint,
            token="bootstrap_test_token",
            use_mock=False,
        )
        applied_live = await bootstrap_schema(client=live_client)
        assert "definition board_token" in applied_live
