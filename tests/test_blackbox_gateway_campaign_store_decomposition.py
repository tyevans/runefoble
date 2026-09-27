"""Blackbox tests verifying Gateway Campaign Store Modular Decomposition (TASK-0221).

Governing ADRs: ADR-0003, ADR-0007.
Verifies modular package structure under gateway/api/src/gateway_api/campaign_store/,
strict file line length limits (< 160 lines per submodule), full backward compatibility
for existing imports, and end-to-end frontdoor HTTP operations for campaigns and invites.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_api.campaign_store import (
    DEFAULT_BOARD_TOKENS,
    DEFAULT_SESSION_PARTICIPANTS,
    CampaignMemberRecord,
    CampaignRecord,
    CampaignStore,
    InviteManager,
    InviteRecord,
    InviteTokenRecord,
    build_campaign_summary,
    campaign_store,
    format_invite_response,
    get_all_viewable_campaigns,
    get_campaign_members,
    get_user_campaign_role,
    join_from_invite,
)
from gateway_api.campaign_store.invites import (
    calculate_invite_expiry,
    generate_invite_token,
)
from gateway_api.campaign_store.models import (
    CampaignMemberRecord as DirectMemberRecord,
)
from gateway_api.campaign_store.models import (
    CampaignRecord as DirectCampaignRecord,
)
from gateway_api.campaign_store.models import (
    InviteTokenRecord as DirectInviteRecord,
)
from gateway_api.campaign_store.queries import (
    build_campaign_summary as direct_build_summary,
)
from gateway_api.campaign_store.queries import (
    get_all_viewable_campaigns as direct_get_all,
)
from gateway_api.campaign_store.queries import (
    get_campaign_members as direct_get_members,
)
from gateway_api.campaign_store.queries import (
    get_user_campaign_role as direct_get_role,
)
from gateway_api.campaign_store.store import (
    CampaignStore as DirectCampaignStore,
)
from gateway_api.campaign_store.store import (
    campaign_store as direct_campaign_store,
)
from gateway_api.main import app as gateway_app

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def clean_store():
    campaign_store.reset()
    yield
    campaign_store.reset()


@pytest.fixture
def client():
    return TestClient(gateway_app)


def test_modular_file_lengths_and_structure():
    """Verify Hard Invariant 6: All campaign store submodules are strictly < 160 lines."""
    store_dir = REPO_ROOT / "gateway/api/src/gateway_api/campaign_store"
    assert store_dir.is_dir(), f"{store_dir} must exist as a package directory"

    # Old monolithic file must not exist
    old_file = REPO_ROOT / "gateway/api/src/gateway_api/campaign_store.py"
    assert not old_file.exists(), "Old monolithic campaign_store.py must be removed"

    expected_modules = {
        "__init__.py": 160,
        "models.py": 120,
        "invites.py": 100,
        "queries.py": 160,
        "store.py": 160,
    }

    for filename, max_lines in expected_modules.items():
        file_path = store_dir / filename
        assert file_path.is_file(), f"Expected module {filename} does not exist in {store_dir}"
        lines = len(file_path.read_text(encoding="utf-8").splitlines())
        assert lines < max_lines, (
            f"{filename} has {lines} lines, exceeding the limit of {max_lines} lines"
        )


def test_package_facade_and_direct_submodule_exports():
    """Verify complete backward compatibility between facade and direct submodule imports."""
    assert CampaignStore is DirectCampaignStore
    assert campaign_store is direct_campaign_store
    assert CampaignRecord is DirectCampaignRecord
    assert CampaignMemberRecord is DirectMemberRecord
    assert InviteTokenRecord is DirectInviteRecord
    assert InviteRecord is InviteTokenRecord
    assert InviteManager is not None
    assert callable(join_from_invite)

    assert build_campaign_summary is direct_build_summary
    assert get_all_viewable_campaigns is direct_get_all
    assert get_campaign_members is direct_get_members
    assert get_user_campaign_role is direct_get_role

    assert len(DEFAULT_BOARD_TOKENS) >= 2
    assert len(DEFAULT_SESSION_PARTICIPANTS) >= 2


def test_record_models_dictionary_serialization():
    """Verify dictionary and summary serialization for all campaign store dataclasses."""
    camp = CampaignRecord(
        id="camp-test-1",
        title="Curse of Strahd",
        description="Gothic horror in Barovia",
        setting="Ravenloft",
        system="5e",
        owner_id="user-dm-1",
        settings={"ambient_theme": "gloomy"},
    )
    d = camp.to_dict()
    assert d["id"] == "camp-test-1"
    assert d["title"] == "Curse of Strahd"
    assert d["setting"] == "Ravenloft"
    assert d["settings"] == {"ambient_theme": "gloomy"}

    summary = camp.to_summary(role="owner", member_count=4)
    assert summary.id == "camp-test-1"
    assert summary.role == "owner"
    assert summary.member_count == 4

    member = CampaignMemberRecord(
        user_id="user-player-1",
        campaign_id="camp-test-1",
        role="player",
    )
    m_dict = member.to_dict()
    assert m_dict["user_id"] == "user-player-1"
    assert m_dict["role"] == "player"
    assert "joined_at" in m_dict

    token_rec = InviteTokenRecord(
        token="inv-tok-123",
        campaign_id="camp-test-1",
        role="player",
        created_by="user-dm-1",
    )
    t_dict = token_rec.to_dict()
    assert t_dict["token"] == "inv-tok-123"
    assert t_dict["role"] == "player"


def test_invite_token_generation_and_validation():
    """Verify secure invite token generation, expiry calculation, and usability checks."""
    token = generate_invite_token()
    assert isinstance(token, str) and len(token) > 16

    expiry = calculate_invite_expiry(24)
    assert expiry is not None
    assert expiry > datetime.now(UTC)

    # Valid invite
    valid_inv = InviteTokenRecord(
        token="valid-tok",
        campaign_id="c1",
        role="player",
        created_by="u1",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        max_uses=2,
        uses=0,
    )
    is_valid, err = valid_inv.validate_usability()
    assert is_valid is True
    assert err is None

    # Expired invite
    expired_inv = InviteTokenRecord(
        token="exp-tok",
        campaign_id="c1",
        role="player",
        created_by="u1",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    is_valid, err = expired_inv.validate_usability()
    assert is_valid is False
    assert err == "Invite token has expired"

    # Exhausted max uses
    exhausted_inv = InviteTokenRecord(
        token="exh-tok",
        campaign_id="c1",
        role="player",
        created_by="u1",
        max_uses=3,
        uses=3,
    )
    is_valid, err = exhausted_inv.validate_usability()
    assert is_valid is False
    assert err == "Invite token usage limit reached"


def test_campaign_store_mutations_and_invites():
    """Verify in-memory CampaignStore CRUD, invite management, and reset operations."""
    store = CampaignStore()
    camp = store.create_campaign(
        campaign_id="camp-alpha",
        title="Tomb of Annihilation",
        owner_id="dm-user-42",
        description="Jungle crawl",
    )
    assert camp.id == "camp-alpha"
    assert store.get_campaign("camp-alpha") is camp
    assert len(store.list_campaigns()) == 1

    # Update campaign
    updated = store.update_campaign("camp-alpha", description="Deep jungle expedition")
    assert updated is not None
    assert updated.description == "Deep jungle expedition"

    # Create invite
    inv = store.create_invite("camp-alpha", "player", "dm-user-42", expires_in_hours=48, max_uses=5)
    assert inv.token in store._invites
    assert store.get_invite(inv.token) is inv

    # Format response
    resp = format_invite_response(inv)
    assert resp.token == inv.token
    assert resp.invite_url == f"/#/join/{inv.token}"

    # Use invite
    used_inv, err = store.use_invite(inv.token)
    assert err is None
    assert used_inv is not None
    assert used_inv.uses == 1

    # Reset
    store.reset()
    assert len(store.list_campaigns()) == 0
    assert len(store._invites) == 0


def test_frontdoor_campaign_creation_and_invite_redemption(client):
    """Blackbox TDD: Public HTTP frontdoor workflow for campaign creation, invites, and join."""
    owner_headers = {"X-User-Id": "dm_frontdoor"}
    player_headers = {"X-User-Id": "player_frontdoor"}

    # 1. Create campaign via HTTP POST
    create_payload = {
        "title": f"Dragon of Icespire Peak {uuid4().hex[:6]}",
        "description": "Frontdoor modular test campaign",
        "setting": "Sword Coast",
        "system": "5e",
        "settings": {"turn_timer_seconds": 60},
    }
    create_res = client.post("/api/v1/campaigns", json=create_payload, headers=owner_headers)
    assert create_res.status_code == 201
    camp_data = create_res.json()
    campaign_id = camp_data["id"]
    assert camp_data["title"] == create_payload["title"]

    # 2. Create invite via HTTP POST
    invite_res = client.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json={"role": "player", "expires_in_hours": 24, "max_uses": 2},
        headers=owner_headers,
    )
    assert invite_res.status_code == 201
    inv_data = invite_res.json()
    token = inv_data["token"]
    assert inv_data["campaign_id"] == campaign_id
    assert inv_data["role"] == "player"

    # 3. Redeem invite via HTTP POST
    join_res = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": token},
        headers=player_headers,
    )
    assert join_res.status_code == 200
    join_data = join_res.json()
    assert join_data["status"] == "joined"
    assert join_data["campaign_id"] == campaign_id
    assert join_data["user_id"] == "player_frontdoor"
    assert join_data["role"] == "player"

    # 4. Verify membership via HTTP GET
    members_res = client.get(
        f"/api/v1/campaigns/{campaign_id}/members",
        headers=owner_headers,
    )
    assert members_res.status_code == 200
    members = members_res.json()
    member_user_ids = {m["user_id"] for m in members}
    assert "dm_frontdoor" in member_user_ids
    assert "player_frontdoor" in member_user_ids
