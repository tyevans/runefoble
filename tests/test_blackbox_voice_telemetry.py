"""Blackbox test: peer telemetry is not stored as domain events (TASK-0577).

Telemetry is best effort and not durable. A burst of telemetry frames writes no events to the
event store. The room summary still shows the latest sample for each peer.

Interacts through public frontdoors only:
  - WebSocket `/ws/voice/{session_id}` (peer join and `webrtc_telemetry` frames)
  - HTTP `GET /api/v1/voice/rooms/{session_id}` (room summary)

`record_appends` spies on `append` for the process event store. No application code is mocked.
"""

from __future__ import annotations

import pytest

from tests.helpers.event_store_seam import record_appends
from tests.helpers.voice_identity import voice_auth_headers
from tests.helpers.ws_identity import ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer", "trusted_voice_issuer")

BURST = 100


def test_telemetry_burst_writes_no_events_and_summary_shows_latest(gateway, table_for):
    user_id = "user-telemetry-burst"
    listener_id = "user-telemetry-listener"
    peer_id = "peer-telemetry-burst"
    _, session_id = table_for("dm_dora", {user_id: "player", listener_id: "player"})

    with (
        gateway.websocket_connect(
            f"/ws/voice/{session_id}?peer_id={peer_id}", subprotocols=ws_subprotocols(user_id)
        ) as ws,
        gateway.websocket_connect(
            f"/ws/voice/{session_id}?peer_id=peer-telemetry-listener",
            subprotocols=ws_subprotocols(listener_id),
        ) as listener,
    ):
        ws.receive_json()
        ws.receive_json()
        listener.receive_json()
        listener.receive_json()

        with record_appends() as saved:
            for i in range(BURST):
                ws.send_json(
                    {
                        "type": "webrtc_telemetry",
                        "peer_id": peer_id,
                        "audio_level": i / 100,
                        "latency_ms": float(i),
                        "is_speaking": i % 2 == 0,
                    }
                )
            # The listener gets one broadcast per telemetry frame. Those broadcasts are the barrier.
            received = 0
            while received < BURST:
                frame = listener.receive_json()
                if frame.get("type") == "webrtc_telemetry":
                    received += 1

        summary = gateway.get(
            f"/api/v1/voice/rooms/{session_id}", headers=voice_auth_headers(user_id)
        ).json()
        peer = summary["participants"][0]
        last = BURST - 1
        assert peer["peer_id"] == peer_id
        assert peer["latency_ms"] == float(last)
        assert peer["audio_level"] == last / 100
        assert peer["is_speaking"] is (last % 2 == 0)

    assert saved == []
