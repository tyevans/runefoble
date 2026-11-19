"""Merchant haggling gambits, DM overrides, bulletin board postings, and cipher decryption."""

from __future__ import annotations

from fastapi.testclient import TestClient
from game_session.events import STREAM_TAVERN, STREAM_WEST_MARCHES
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.stream_events import assert_stream_events

from .conftest import setup_campaign_settlement, ws_subprotocols


def test_merchant_haggling_gambits_and_dm_override(
    session_client: TestClient, mock_bus: MockAsyncRedis
) -> None:
    """Simulate persuasion rolls against merchant temperament and verify DM mood adjustment."""
    cid, sid, _, dm_h, p_h = setup_campaign_settlement(session_client, ["artisan"])
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
    assert_stream_events(mock_bus, "GambitExecuted", stream=STREAM_TAVERN)

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
    assert_stream_events(mock_bus, "NegotiationConcluded", stream=STREAM_TAVERN)
    assert_stream_events(mock_bus, "CurrencyDeducted", stream=STREAM_TAVERN)


def test_bulletin_board_pin_and_cipher_decrypt(
    session_client: TestClient,
    gateway_client: TestClient,
    mock_bus: MockAsyncRedis,
    settlement_issuer: SigningTestIssuer,
) -> None:
    """Post bounty, decrypt hidden cipher notice, and verify WebSocket party broadcast."""
    cid, sid, p_id, dm_h, p_h = setup_campaign_settlement(session_client, issuer=settlement_issuer)

    bulletin = f"/api/v1/settlements/{sid}/bulletin"

    b_data = {"board_type": "town_square", "title": "Wyvern", "category": "bounty"} | {
        "content": "300gp",
        "wax_sealed": True,
        "metadata": {"reward_gp": 300},
    }
    bounty = session_client.post(bulletin, json=b_data, headers=dm_h)
    assert bounty.status_code == 201 and bounty.json()["wax_sealed"] is True
    assert_stream_events(mock_bus, "BulletinNoticePinned", stream=STREAM_WEST_MARCHES)

    secret_text = "Midnight meeting behind the apothecary."
    c_data = {"board_type": "tavern", "title": "Meeting", "category": "rumor"} | {
        "content": "Note",
        "cipher_encoded": True,
        "cipher_solution": "gilded night",
        "hidden_content": secret_text,
    }
    nid = session_client.post(bulletin, json=c_data, headers=dm_h).json()["notice_id"]

    notices = session_client.get(bulletin, headers=p_h).json()
    assert any(
        n["notice_id"] == nid and not n["is_decrypted"] and not n["hidden_content"] for n in notices
    )

    dec = session_client.post(
        f"{bulletin}/{nid}/decrypt", json={"solution": "gilded night"}, headers=p_h
    )
    assert dec.status_code == 200 and dec.json()["decrypted_content"] == secret_text
    assert_stream_events(mock_bus, "CipherNoticeDecrypted", stream=STREAM_WEST_MARCHES)

    ws_url = f"/ws/campaigns/{cid}"
    with (
        gateway_client.websocket_connect(ws_url, subprotocols=ws_subprotocols(dm_h)) as ws_dm,
        gateway_client.websocket_connect(ws_url, subprotocols=ws_subprotocols(p_h)) as ws_player,
    ):
        assert ws_dm.receive_json()["type"] == "connected"
        assert ws_player.receive_json()["type"] == "connected"
        # The socket relays only server-defined actions (TASK-0544). A client-defined bulletin
        # action gets an UNKNOWN_ACTION error, and nothing reaches the other player.
        ws_dm.send_json(
            {"action": "bulletin_bounty_posted", "settlement_id": sid, "notice_id": nid}
            | {"title": "Meeting", "is_decrypted": True}
        )
        error = ws_dm.receive_json()
        assert error["type"] == "error" and error["code"] == "UNKNOWN_ACTION"
        assert error["action"] == "bulletin_bounty_posted"
