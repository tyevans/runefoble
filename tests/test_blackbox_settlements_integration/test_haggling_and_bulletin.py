"""Merchant haggling gambits, DM overrides, bulletin board postings, and cipher decryption."""

from __future__ import annotations

from fastapi.testclient import TestClient
from game_session.dependencies import STREAM_TAVERN, STREAM_WEST_MARCHES
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis

from .conftest import assert_stream_event, setup_campaign_settlement


def test_merchant_haggling_gambits_and_dm_override(
    session_client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Simulate persuasion rolls against merchant temperament and verify DM mood adjustment."""
    cid, sid, _, dm_h, p_h = setup_campaign_settlement(session_client, spicedb, ["artisan"])
    eid = session_client.post(
        f"/api/v1/settlements/{sid}/establishments",
        json={"district_id": "artisan", "category": "commerce", "name": "Bram's Anvil"},
        headers=dm_h,
    ).json()["establishment_id"]

    h_data = {
        "character_id": "char_alys",
        "item_id": "blade",
        "item_name": "Blade",
        "base_price": 350,
    } | {
        "initial_offer_gp": 260,
        "gambit": "bulk_order_promise",
        "roll_value": 18,
        "campaign_id": cid,
        "temperament": "Stubborn",
    }
    haggle = session_client.post(
        f"/api/v1/establishments/{eid}/haggle", json=h_data, headers=p_h
    ).json()
    neg_id = haggle["negotiation_id"]
    assert haggle["status"] == "active" and haggle["counter_price"] < 350
    assert_stream_event(mock_bus, STREAM_TAVERN, "GambitExecuted")

    flatt = session_client.post(
        f"/api/v1/haggling/{neg_id}/gambit",
        json={"character_id": "char_alys", "gambit": "flattery", "roll_value": 16},
        headers=p_h,
    ).json()
    assert flatt["counter_price"] <= haggle["counter_price"]

    def _dm_patch(d: dict):
        return session_client.patch(f"/api/v1/haggling/{neg_id}/dm-override", json=d, headers=dm_h)

    soothe = _dm_patch(
        {"action": "soothe_merchant", "narrative_bark": "The blacksmith nods warmly."}
    )
    assert soothe.status_code == 200 and soothe.json()["merchant_mood_score"] > 0

    accept = _dm_patch(
        {"action": "force_accept", "override_price_gp": 275, "narrative_bark": "Deal closed."}
    )
    assert accept.status_code == 200 and accept.json()["status"] == "completed"
    assert accept.json()["counter_price"] == 275
    assert_stream_event(mock_bus, STREAM_TAVERN, "NegotiationConcluded")
    assert_stream_event(mock_bus, STREAM_TAVERN, "CurrencyDeducted")


def test_bulletin_board_pin_and_cipher_decrypt(
    session_client: TestClient,
    gateway_client: TestClient,
    spicedb: MockSpiceDBClient,
    mock_bus: MockAsyncRedis,
) -> None:
    """Post bounty, decrypt hidden cipher notice, and verify WebSocket party broadcast."""
    cid, sid, p_id, dm_h, p_h = setup_campaign_settlement(session_client, spicedb)
    dm_id, base_url = dm_h["x-user-id"], f"/api/v1/settlements/{sid}/bulletin"

    def _post_dm(data: dict):
        return session_client.post(base_url, json=data, headers=dm_h)

    b_data = {"board_type": "town_square", "title": "Wyvern", "category": "bounty"} | {
        "content": "300gp",
        "wax_sealed": True,
        "metadata": {"reward_gp": 300},
    }
    bounty = _post_dm(b_data)
    assert bounty.status_code == 201 and bounty.json()["wax_sealed"] is True
    assert_stream_event(mock_bus, STREAM_WEST_MARCHES, "BulletinNoticePinned")

    secret_text = "Midnight meeting behind the apothecary."
    c_data = {"board_type": "tavern", "title": "Meeting", "category": "rumor"} | {
        "content": "Note",
        "cipher_encoded": True,
        "cipher_solution": "gilded night",
        "hidden_content": secret_text,
    }
    nid = _post_dm(c_data).json()["notice_id"]

    notices = session_client.get(base_url, headers=p_h).json()
    assert any(
        n["notice_id"] == nid and not n["is_decrypted"] and not n["hidden_content"] for n in notices
    )

    dec = session_client.post(
        f"{base_url}/{nid}/decrypt", json={"solution": "gilded night"}, headers=p_h
    )
    assert dec.status_code == 200 and dec.json()["decrypted_content"] == secret_text
    assert_stream_event(mock_bus, STREAM_WEST_MARCHES, "CipherNoticeDecrypted")

    with (
        gateway_client.websocket_connect(f"/ws/campaigns/{cid}?user_id={dm_id}") as ws_dm,
        gateway_client.websocket_connect(f"/ws/campaigns/{cid}?user_id={p_id}") as ws_player,
    ):
        assert ws_dm.receive_json()["type"] == "connected"
        assert ws_player.receive_json()["type"] == "connected"
        ws_dm.send_json(
            {"action": "bulletin_bounty_posted", "settlement_id": sid, "notice_id": nid}
            | {"title": "Meeting", "is_decrypted": True}
        )
        assert ws_dm.receive_json()["action"] == "bulletin_bounty_posted"
        f_p = ws_player.receive_json()
        assert (
            f_p["action"] == "bulletin_bounty_posted"
            and f_p["notice_id"] == nid
            and f_p["is_decrypted"]
        )
