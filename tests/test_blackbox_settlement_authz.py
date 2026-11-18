"""Frontdoor blackbox tests for settlement, haggling, and bulletin authorization.

Part of TASK-0549 / US-0047 / US-0072 / US-0075 / US-0076 / ADR-0001 / ADR-0014.

Every test calls public HTTP routes with signed bearer tokens. Membership and
settlement ownership come from the campaign and settlement frontdoors. No test
writes a SpiceDB tuple directly.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as session_app

from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


def _headers(sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def tc() -> TestClient:
    return TestClient(session_app)


@pytest.fixture
def haven(tc: TestClient) -> tuple[str, str]:
    """Create a campaign owned by `gm-<hex>` and charter a settlement in it through the frontdoor.

    Returns (settlement_id, founder_sub). The founder is the campaign owner.
    """
    founder = f"gm-{uuid4().hex[:8]}"
    created = tc.post(
        "/api/v1/campaigns", json={"title": "Frontier Watch"}, headers=_headers(founder)
    )
    assert created.status_code == 201
    campaign_id = created.json()["id"]
    charter = tc.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={"name": "Garrison Prime", "scale": "village", "districts": ["market"]},
        headers=_headers(founder),
    )
    assert charter.status_code == 201
    return charter.json()["settlement_id"], founder


def test_anonymous_upgrade_tier_is_refused(tc: TestClient, haven: tuple[str, str]):
    """A request without a principal gets 401, never a state change."""
    settlement_id, _ = haven
    res = tc.post(f"/api/v1/settlements/{settlement_id}/upgrade-tier", json={})
    assert res.status_code == 401


def test_stranger_cannot_upgrade_tier_and_founder_can(tc: TestClient, haven: tuple[str, str]):
    """A verified stranger gets 403. The founder gets 200."""
    settlement_id, founder = haven
    stranger = _headers(f"stranger-{uuid4().hex[:8]}")

    denied = tc.post(f"/api/v1/settlements/{settlement_id}/upgrade-tier", json={}, headers=stranger)
    assert denied.status_code == 403

    allowed = tc.post(
        f"/api/v1/settlements/{settlement_id}/upgrade-tier",
        json={"new_tier": 3, "prosperity": 300},
        headers=_headers(founder),
    )
    assert allowed.status_code == 200, allowed.text


def test_player_role_header_does_not_bypass_dm_override(tc: TestClient):
    """The X-RuneFoble-Role header grants nothing. Arbitration needs negotiation.arbitrate."""
    player = f"player-{uuid4().hex[:8]}"
    res = tc.patch(
        f"/api/v1/haggling/{uuid4()}/dm-override",
        json={"action": "nudge", "mood_delta": 1},
        headers={**_headers(player), "X-RuneFoble-Role": "dm"},
    )
    assert res.status_code == 403


def test_haggle_without_principal_is_refused(tc: TestClient):
    """Opening a negotiation without a verified principal gets 401."""
    res = tc.post(
        f"/api/v1/establishments/{uuid4()}/haggle",
        json={"character_id": "char_1", "item_id": "item_1"},
    )
    assert res.status_code == 401


def test_bulletin_decrypt_by_non_viewer_is_refused(tc: TestClient, haven: tuple[str, str]):
    """A verified caller with no view right on the settlement gets 403 on decrypt."""
    settlement_id, founder = haven
    pinned = tc.post(
        f"/api/v1/settlements/{settlement_id}/bulletin",
        json={"title": "Wolf bounty", "content": "Wolves at the ford."},
        headers=_headers(founder),
    )
    assert pinned.status_code == 201
    notice_id = pinned.json()["notice_id"]

    stranger = _headers(f"stranger-{uuid4().hex[:8]}")
    res = tc.post(
        f"/api/v1/settlements/{settlement_id}/bulletin/{notice_id}/decrypt",
        json={"solution": "open sesame"},
        headers=stranger,
    )
    assert res.status_code == 403


@pytest.fixture
def establishment_with_worker(tc: TestClient, haven: tuple[str, str]) -> tuple[str, str, str]:
    """Construct an establishment and assign a worker through the frontdoors.

    Returns (establishment_id, npc_id, founder_sub). The founder is the campaign owner.
    """
    settlement_id, founder = haven
    constructed = tc.post(
        f"/api/v1/settlements/{settlement_id}/establishments",
        json={"district_id": "market", "category": "commerce", "name": "Forge"},
        headers=_headers(founder),
    )
    assert constructed.status_code == 201, constructed.text
    establishment_id = constructed.json()["establishment_id"]
    assigned = tc.post(
        f"/api/v1/establishments/{establishment_id}/workers",
        json={"name": "Torvin", "role": "apprentice"},
        headers=_headers(founder),
    )
    assert assigned.status_code == 201, assigned.text
    return establishment_id, assigned.json()["npc_id"], founder


def test_anonymous_worker_mood_change_is_refused(
    tc: TestClient, establishment_with_worker: tuple[str, str, str]
):
    """A worker mood change without a principal gets 401."""
    _, npc_id, _ = establishment_with_worker
    res = tc.patch(
        f"/api/v1/npcs/{npc_id}/mood",
        json={"mood": "calm", "temperament": "patient"},
    )
    assert res.status_code == 401


def test_stranger_cannot_change_worker_mood_and_manager_can(
    tc: TestClient, establishment_with_worker: tuple[str, str, str]
):
    """npc.edit_mood is required. A stranger gets 403. The campaign owner gets 200."""
    _, npc_id, founder = establishment_with_worker
    body = {"mood": "calm", "temperament": "patient"}
    denied = tc.patch(
        f"/api/v1/npcs/{npc_id}/mood",
        json=body,
        headers=_headers(f"stranger-{uuid4().hex[:8]}"),
    )
    assert denied.status_code == 403

    allowed = tc.patch(f"/api/v1/npcs/{npc_id}/mood", json=body, headers=_headers(founder))
    assert allowed.status_code == 200, allowed.text


def test_stranger_cannot_assign_or_relieve_workers(
    tc: TestClient, establishment_with_worker: tuple[str, str, str]
):
    """establishment.manage guards assignment and relief. A stranger gets 403."""
    establishment_id, npc_id, _ = establishment_with_worker
    stranger = _headers(f"stranger-{uuid4().hex[:8]}")
    assigned = tc.post(
        f"/api/v1/establishments/{establishment_id}/workers",
        json={"name": "Mallory", "role": "apprentice"},
        headers=stranger,
    )
    assert assigned.status_code == 403

    relieved = tc.post(
        f"/api/v1/establishments/{establishment_id}/workers/{npc_id}/relieve",
        json={"reason": "fired"},
        headers=stranger,
    )
    assert relieved.status_code == 403


def test_stranger_cannot_record_worker_relationship(
    tc: TestClient, establishment_with_worker: tuple[str, str, str]
):
    """npc.manage guards relationships. A stranger gets 403."""
    _, npc_id, _ = establishment_with_worker
    res = tc.post(
        f"/api/v1/npcs/{npc_id}/relationships",
        json={"target_npc": "npc-other", "relation": "rival"},
        headers=_headers(f"stranger-{uuid4().hex[:8]}"),
    )
    assert res.status_code == 403
