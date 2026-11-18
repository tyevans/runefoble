"""Blackbox frontdoor tests for rules compendium homebrew authorization (TASK-0555).

Governing ADRs: ADR-0001 (SpiceDB Zanzibar object authorization), ADR-0007 (compendium owns
homebrew, campaign relation is written by the campaign context), ADR-0014 (BDD through public routes).

Setup goes through public routes only: the owner creates a campaign on the gateway, and members
redeem invites there. The compendium is then probed through its own public routes. Both apps share
the factory SpiceDB double, so the grants made by the gateway are what the compendium checks.
No test writes a tuple directly.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from rules_compendium.main import app as compendium_app
from runefoble_auth.errors import AuthzWriteError
from runefoble_auth.factory import get_spicedb_client

HOMEBREW_PAYLOAD = {
    "rule_type": "monster",
    "title": "Abyssal Shadowstalker",
    "content": {"challenge_rating": 3.0, "creature_type": "fiend", "hit_points": 45},
}


@pytest.fixture
def gateway(game_session_upstream, character_sheet_upstream) -> TestClient:
    """Enter the gateway lifespan after the upstream services are served."""
    with TestClient(gateway_app) as client:
        yield client


@pytest.fixture
def compendium() -> TestClient:
    with TestClient(compendium_app) as client:
        yield client


def _auth(issuer, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


def _campaign_with_cast(gateway, issuer) -> tuple[str, dict[str, str]]:
    """Create a campaign as owner_orin. Redeem a spectator invite as the DM, then grant DM.

    The player redeems a player invite.

    Returns the campaign id and the owner's headers.
    """
    owner = _auth(issuer, "owner_orin")
    created = gateway.post("/api/v1/campaigns", json={"title": "Homebrew Test"}, headers=owner)
    assert created.status_code == 201, created.text
    campaign_id = created.json()["id"]
    for role, sub in (("spectator", "dm_sable"), ("player", "player_tamsin")):
        _join_with_invite(gateway, issuer, campaign_id, owner, role, sub)
    grant = gateway.post(
        f"/api/v1/campaigns/{campaign_id}/roles",
        json={"user_id": "dm_sable", "role": "dungeon_master"},
        headers=owner,
    )
    assert grant.status_code in (200, 201), grant.text
    return campaign_id, owner


def _join_with_invite(gateway, issuer, campaign_id: str, owner: dict, role: str, sub: str) -> None:
    """Create an invite as the owner, then redeem it as `sub`."""
    inv = gateway.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json={"role": role},
        headers=owner,
    )
    assert inv.status_code == 201, inv.text
    join = gateway.post(
        "/api/v1/campaigns/join",
        json={"invite_token": inv.json()["token"]},
        headers=_auth(issuer, sub),
    )
    assert join.status_code == 200, join.text


def _register(compendium, campaign_id: str, headers: dict[str, str]):
    return compendium.post(
        "/api/v1/compendium/homebrew",
        json={"campaign_id": campaign_id, **HOMEBREW_PAYLOAD},
        headers=headers,
    )


def _list(compendium, campaign_id: str, headers: dict[str, str]) -> list[dict]:
    res = compendium.get(f"/api/v1/compendium/homebrew/{campaign_id}", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def _search(compendium, campaign_id: str, headers: dict[str, str]) -> list[dict]:
    res = compendium.get(
        "/api/v1/compendium/rules/search",
        params={"query": "Shadowstalker", "campaign_id": campaign_id},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    return res.json()["results"]


def test_anonymous_homebrew_list_is_refused(gateway, compendium, trusted_ws_issuer):
    """With no bearer, the list route returns 401 and shows no homebrew."""
    campaign_id, owner = _campaign_with_cast(gateway, trusted_ws_issuer)
    assert (
        _register(compendium, campaign_id, _auth(trusted_ws_issuer, "dm_sable")).status_code == 200
    )

    res = compendium.get(f"/api/v1/compendium/homebrew/{campaign_id}")
    assert res.status_code == 401, res.text


def test_anonymous_search_with_campaign_is_refused(gateway, compendium, trusted_ws_issuer):
    """With no bearer, a campaign search returns 401. No homebrew hit leaks."""
    campaign_id, _ = _campaign_with_cast(gateway, trusted_ws_issuer)
    assert (
        _register(compendium, campaign_id, _auth(trusted_ws_issuer, "dm_sable")).status_code == 200
    )

    res = compendium.get(
        "/api/v1/compendium/rules/search",
        params={"query": "Shadowstalker", "campaign_id": campaign_id},
    )
    assert res.status_code == 401, res.text


def test_campaign_members_see_homebrew_and_strangers_do_not(gateway, compendium, trusted_ws_issuer):
    """The DM and player see the rule in the list and in search. A stranger sees neither."""
    campaign_id, _ = _campaign_with_cast(gateway, trusted_ws_issuer)
    dm = _auth(trusted_ws_issuer, "dm_sable")
    player = _auth(trusted_ws_issuer, "player_tamsin")
    stranger = _auth(trusted_ws_issuer, "stranger_vex")

    created = _register(compendium, campaign_id, dm)
    assert created.status_code == 200, created.text
    rule_id = created.json()["rule_id"]

    for headers in (dm, player):
        listed = _list(compendium, campaign_id, headers)
        assert [r["rule_id"] for r in listed] == [rule_id]
        assert any(
            r["name"] == "Abyssal Shadowstalker" for r in _search(compendium, campaign_id, headers)
        )

    assert _list(compendium, campaign_id, stranger) == []
    assert not any(
        r["name"] == "Abyssal Shadowstalker" for r in _search(compendium, campaign_id, stranger)
    )


def test_player_post_is_forbidden_and_writes_nothing(gateway, compendium, trusted_ws_issuer):
    """A redeemed player gets 403 and no rule is saved. A spoofed user header changes nothing."""
    campaign_id, _ = _campaign_with_cast(gateway, trusted_ws_issuer)
    player = _auth(trusted_ws_issuer, "player_tamsin")

    res = _register(compendium, campaign_id, player)
    assert res.status_code == 403, res.text

    spoofed = compendium.post(
        "/api/v1/compendium/homebrew",
        json={"campaign_id": campaign_id, **HOMEBREW_PAYLOAD},
        headers={"x-user-id": "dm_sable"},
    )
    assert spoofed.status_code == 401, spoofed.text

    assert _list(compendium, campaign_id, _auth(trusted_ws_issuer, "dm_sable")) == []


def test_stranger_post_is_forbidden(gateway, compendium, trusted_ws_issuer):
    """A verified user with no campaign grant gets 403."""
    campaign_id, _ = _campaign_with_cast(gateway, trusted_ws_issuer)

    res = _register(compendium, campaign_id, _auth(trusted_ws_issuer, "stranger_vex"))
    assert res.status_code == 403, res.text


def test_dm_post_is_saved_under_the_token_subject(gateway, compendium, trusted_ws_issuer):
    """The DM gets 200. The author is the token subject, never a body or header value."""
    campaign_id, _ = _campaign_with_cast(gateway, trusted_ws_issuer)

    res = _register(compendium, campaign_id, _auth(trusted_ws_issuer, "dm_sable"))
    assert res.status_code == 200, res.text
    assert res.json()["author_id"] == "dm_sable"


def test_spicedb_write_failure_returns_503_and_saves_no_rule(
    gateway, compendium, trusted_ws_issuer, monkeypatch
):
    """A failed Zanzibar write returns 503. The rule is not saved."""
    campaign_id, _ = _campaign_with_cast(gateway, trusted_ws_issuer)
    dm = _auth(trusted_ws_issuer, "dm_sable")
    client = get_spicedb_client()

    async def refuse_write(*args, **kwargs):
        raise AuthzWriteError("simulated SpiceDB write refusal")

    monkeypatch.setattr(client, "write_relationship", refuse_write)

    res = _register(compendium, campaign_id, dm)
    assert res.status_code == 503, res.text

    monkeypatch.undo()
    assert _list(compendium, campaign_id, dm) == []


def test_encounter_naming_a_campaign_requires_play(gateway, compendium, trusted_ws_issuer):
    """A campaign-scoped balance call needs `campaign.play`. A stranger gets 403."""
    campaign_id, _ = _campaign_with_cast(gateway, trusted_ws_issuer)
    body = {"party_levels": [3, 3, 3, 3], "target_difficulty": "Medium", "campaign_id": campaign_id}

    stranger = compendium.post(
        "/api/v1/compendium/encounters/balance",
        json=body,
        headers=_auth(trusted_ws_issuer, "stranger_vex"),
    )
    assert stranger.status_code == 403, stranger.text

    player = compendium.post(
        "/api/v1/compendium/encounters/balance",
        json=body,
        headers=_auth(trusted_ws_issuer, "player_tamsin"),
    )
    assert player.status_code == 200, player.text


def test_encounter_without_campaign_needs_only_a_token(compendium, trusted_ws_issuer):
    """A balance call that names no campaign succeeds for any verified user."""
    res = compendium.post(
        "/api/v1/compendium/encounters/balance",
        json={"party_levels": [2, 2], "target_difficulty": "Easy"},
        headers=_auth(trusted_ws_issuer, "stranger_vex"),
    )
    assert res.status_code == 200, res.text


def _monster(compendium, name: str, headers: dict[str, str], campaign_id: str | None = None):
    params = {"campaign_id": campaign_id} if campaign_id else None
    return compendium.get(f"/api/v1/compendium/monsters/{name}", params=params, headers=headers)


def test_owner_reads_own_homebrew_monster_by_name(gateway, compendium, trusted_ws_issuer):
    """The DM reads the homebrew monster by name when it names the campaign."""
    campaign_id, _ = _campaign_with_cast(gateway, trusted_ws_issuer)
    assert (
        _register(compendium, campaign_id, _auth(trusted_ws_issuer, "dm_sable")).status_code == 200
    )

    res = _monster(
        compendium,
        "Abyssal%20Shadowstalker",
        _auth(trusted_ws_issuer, "dm_sable"),
        campaign_id,
    )
    assert res.status_code == 200, res.text
    assert res.json()["name"] == "Abyssal Shadowstalker"
    assert res.json()["is_homebrew"] is True


def test_stranger_gets_404_for_homebrew_monster(gateway, compendium, trusted_ws_issuer):
    """A verified stranger gets 404 for the campaign homebrew monster, as if it did not exist."""
    campaign_id, _ = _campaign_with_cast(gateway, trusted_ws_issuer)
    assert (
        _register(compendium, campaign_id, _auth(trusted_ws_issuer, "dm_sable")).status_code == 200
    )

    res = _monster(
        compendium,
        "Abyssal%20Shadowstalker",
        _auth(trusted_ws_issuer, "stranger_vex"),
        campaign_id,
    )
    assert res.status_code == 404, res.text


def test_homebrew_monster_needs_a_campaign_to_be_read(gateway, compendium, trusted_ws_issuer):
    """Without `campaign_id`, even the DM gets 404 for a homebrew monster."""
    campaign_id, _ = _campaign_with_cast(gateway, trusted_ws_issuer)
    assert (
        _register(compendium, campaign_id, _auth(trusted_ws_issuer, "dm_sable")).status_code == 200
    )

    res = _monster(compendium, "Abyssal%20Shadowstalker", _auth(trusted_ws_issuer, "dm_sable"))
    assert res.status_code == 404, res.text


def test_srd_monster_is_readable_by_every_token_holder(gateway, compendium, trusted_ws_issuer):
    """An SRD monster is readable by the DM and by a stranger. No bearer gets 401."""
    campaign_id, _ = _campaign_with_cast(gateway, trusted_ws_issuer)

    for sub in ("dm_sable", "stranger_vex"):
        res = _monster(compendium, "Goblin", _auth(trusted_ws_issuer, sub), campaign_id)
        assert res.status_code == 200, res.text
        assert res.json()["name"] == "Goblin"
        assert res.json().get("is_homebrew", False) is False

    assert _monster(compendium, "Goblin", {}).status_code == 401


def _register_goblin(compendium, campaign_id: str, headers: dict[str, str]):
    """Register a homebrew monster named like the SRD Goblin, with CR 99."""
    return compendium.post(
        "/api/v1/compendium/homebrew",
        json={
            "campaign_id": campaign_id,
            "rule_type": "monster",
            "title": "Goblin",
            "content": {"challenge_rating": 99.0, "hit_points": 900},
        },
        headers=headers,
    )


def test_srd_goblin_wins_over_homebrew_goblin_by_name(gateway, compendium, trusted_ws_issuer):
    """A campaign homebrew Goblin never replaces the SRD Goblin, for the DM or anyone else."""
    campaign_id, _ = _campaign_with_cast(gateway, trusted_ws_issuer)
    dm = _auth(trusted_ws_issuer, "dm_sable")
    assert _register_goblin(compendium, campaign_id, dm).status_code == 200

    for params in (None, {"campaign_id": campaign_id}):
        res = compendium.get("/api/v1/compendium/monsters/Goblin", params=params, headers=dm)
        assert res.status_code == 200, res.text
        assert res.json()["challenge_rating"] == 0.25


def test_shadowed_homebrew_is_listed_with_shadowed_flag(gateway, compendium, trusted_ws_issuer):
    """The list keeps the homebrew Goblin and marks it `shadowed` because an SRD entry has its name."""
    campaign_id, _ = _campaign_with_cast(gateway, trusted_ws_issuer)
    dm = _auth(trusted_ws_issuer, "dm_sable")
    assert _register_goblin(compendium, campaign_id, dm).status_code == 200
    assert _register(compendium, campaign_id, dm).status_code == 200

    listed = {rule["title"]: rule for rule in _list(compendium, campaign_id, dm)}
    assert listed["Goblin"]["shadowed"] is True
    assert listed["Goblin"]["content"]["challenge_rating"] == 99.0
    assert listed["Abyssal Shadowstalker"]["shadowed"] is False


def test_search_returns_srd_goblin_not_shadowed_homebrew(gateway, compendium, trusted_ws_issuer):
    """A campaign search for Goblin returns only the SRD entry under that name."""
    campaign_id, _ = _campaign_with_cast(gateway, trusted_ws_issuer)
    dm = _auth(trusted_ws_issuer, "dm_sable")
    assert _register_goblin(compendium, campaign_id, dm).status_code == 200

    res = compendium.get(
        "/api/v1/compendium/rules/search",
        params={"query": "Goblin", "campaign_id": campaign_id},
        headers=dm,
    )
    assert res.status_code == 200, res.text
    goblins = [r for r in res.json()["results"] if r["name"] == "Goblin"]
    assert goblins, res.text
    assert all(r["is_homebrew"] is False for r in goblins)


def test_campaign_homebrew_is_rebuilt_from_events_after_restart(gateway, trusted_ws_issuer):
    """A restarted compendium lists the campaign homebrew again. The events are the source of truth."""
    campaign_id, _ = _campaign_with_cast(gateway, trusted_ws_issuer)
    dm = _auth(trusted_ws_issuer, "dm_sable")
    with TestClient(compendium_app) as before_restart:
        assert _register(before_restart, campaign_id, dm).status_code == 200

    with TestClient(compendium_app) as after_restart:
        listed = _list(after_restart, campaign_id, dm)
        assert [rule["title"] for rule in listed] == ["Abyssal Shadowstalker"]
        assert listed[0]["shadowed"] is False


def test_restarted_compendium_reads_and_searches_rebuilt_homebrew(gateway, trusted_ws_issuer):
    """After a restart, the homebrew monster is readable by a member and found by search."""
    campaign_id, _ = _campaign_with_cast(gateway, trusted_ws_issuer)
    dm = _auth(trusted_ws_issuer, "dm_sable")
    with TestClient(compendium_app) as before_restart:
        assert _register(before_restart, campaign_id, dm).status_code == 200

    with TestClient(compendium_app) as after_restart:
        res = _monster(after_restart, "Abyssal%20Shadowstalker", dm, campaign_id)
        assert res.status_code == 200, res.text
        assert res.json()["name"] == "Abyssal Shadowstalker"

        found = _search(after_restart, campaign_id, dm)
        assert any(r["name"] == "Abyssal Shadowstalker" for r in found)
