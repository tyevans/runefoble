"""Mobile companion WebSocket endpoint handler."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import WebSocket, WebSocketDisconnect
from gateway_api.auth import get_spicedb_client
from gateway_api.companion.manager import (
    MobileCompanionManager,
    mobile_companion_manager,
    publish_companion_event,
)
from gateway_api.signaling.auth import extract_signaling_auth, validate_voice_connection
from runefoble_events.voice import (
    MobileAudioProfileAdapted,
    MobileCompanionConnected,
)
from voice_agent.mobile import (
    PROFILES,
    HapticVibrationPattern,
    MobileAudioProfileTier,
    adapt_audio_profile,
    create_haptic_payload,
)

logger = logging.getLogger("runefoble.gateway.companion.endpoint")


async def mobile_companion_websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    manager: MobileCompanionManager | None = None,
) -> None:
    """Handle low-bandwidth mobile companion WebSockets at /ws/mobile-companion/{session_id}."""
    comp_manager = manager or mobile_companion_manager
    spicedb = get_spicedb_client()
    user_id, peer_id, role = extract_signaling_auth(websocket)

    # 1. SpiceDB Zanzibar permission check on connect (Hard Invariant 1)
    can_connect = await validate_voice_connection(spicedb, session_id, user_id)
    if not can_connect:
        logger.warning(
            "Mobile companion connect rejected: user '%s' lacks permissions for session '%s'",
            user_id,
            session_id,
        )
        await websocket.accept()
        await websocket.send_json(
            {
                "type": "error",
                "code": "PERMISSION_DENIED",
                "message": f"Zanzibar authorization denied: insufficient permissions for session '{session_id}'",
                "action": "connect",
            }
        )
        await websocket.close(code=4003, reason="Forbidden: insufficient permissions")
        return

    await websocket.accept()
    await comp_manager.connect(session_id, user_id, peer_id, websocket)

    # 2. Publish MobileCompanionConnected domain event
    conn_event = MobileCompanionConnected(
        session_id=session_id,
        peer_id=peer_id,
        user_id=user_id,
        device_type="mobile",
        audio_profile_tier=MobileAudioProfileTier.MOBILE_OPTIMIZED,
        haptic_supported=True,
        connected_at=datetime.now(UTC).isoformat(),
    )
    await publish_companion_event("runefoble.events.voice", conn_event)

    # 3. Send initial connected confirmation frame
    init_profile = PROFILES[MobileAudioProfileTier.MOBILE_OPTIMIZED]
    await websocket.send_json(
        {
            "type": "mobile_companion_connected",
            "session_id": session_id,
            "user_id": user_id,
            "peer_id": peer_id,
            "role": role,
            "audio_profile": init_profile.model_dump(),
            "haptic_supported": True,
            "vibration_patterns": {
                "secret_whisper": HapticVibrationPattern.SECRET_WHISPER,
                "turn_alert": HapticVibrationPattern.TURN_ALERT,
                "critical_alert": HapticVibrationPattern.CRITICAL_ALERT,
                "danger_alert": HapticVibrationPattern.DANGER_ALERT,
            },
            "message": "Connected to Runefoble Spatial Companion Mobile Gateway.",
        }
    )

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type") or data.get("action") or "unknown"

            if msg_type == "mobile_telemetry":
                loss = float(data.get("packet_loss", 0.0))
                bw = (
                    float(data.get("bandwidth_kbps"))
                    if data.get("bandwidth_kbps") is not None
                    else None
                )
                lat = float(data.get("latency_ms")) if data.get("latency_ms") is not None else None

                prev_tier = comp_manager.active_profiles.get(session_id, {}).get(
                    user_id, MobileAudioProfileTier.MOBILE_OPTIMIZED
                )
                new_profile, reason = adapt_audio_profile(loss, bw, lat)
                comp_manager.active_profiles.setdefault(session_id, {})[user_id] = new_profile.tier

                response = {
                    "type": "audio_profile_adapted",
                    "session_id": session_id,
                    "user_id": user_id,
                    "previous_tier": prev_tier,
                    "current_tier": new_profile.tier,
                    "profile": new_profile.model_dump(),
                    "reason": reason,
                }
                await websocket.send_json(response)

                adapt_event = MobileAudioProfileAdapted(
                    session_id=session_id,
                    peer_id=peer_id,
                    user_id=user_id,
                    previous_tier=prev_tier,
                    current_tier=new_profile.tier,
                    sample_rate=new_profile.sample_rate,
                    bitrate_kbps=new_profile.bitrate_kbps,
                    packet_loss=loss,
                    reason=reason,
                )
                await publish_companion_event("runefoble.events.voice", adapt_event)

            elif msg_type == "send_whisper":
                target_user = data.get("target_user_id") or data.get("recipient_id") or user_id
                whisper_content = data.get("content", "")
                snd = data.get("sender", "DM")
                await comp_manager.dispatch_whisper(
                    session_id, target_user, whisper_content, sender=snd
                )

            elif msg_type == "trigger_haptic":
                alert_type = data.get("alert_type", "secret_whisper")
                custom_pat = data.get("vibration_pattern") or data.get("custom_pattern")
                payload = create_haptic_payload(
                    session_id=session_id,
                    alert_type=alert_type,
                    custom_pattern=custom_pat,
                    whisper=data.get("whisper"),
                    notification=data.get("notification"),
                    recipient_id=data.get("recipient_id", user_id),
                )
                target_user = data.get("target_user_id") or user_id
                await comp_manager.send_to_user(session_id, target_user, payload)

            elif msg_type == "audio_frame":
                await websocket.send_json(
                    {
                        "type": "audio_frame_ack",
                        "session_id": session_id,
                        "frame_seq": data.get("frame_seq", 0),
                        "status": "received",
                        "sample_rate": data.get("sample_rate", 16000),
                    }
                )

            elif msg_type == "ping":
                await websocket.send_json(
                    {"type": "pong", "timestamp": datetime.now(UTC).isoformat()}
                )

    except WebSocketDisconnect:
        comp_manager.disconnect(websocket)


__all__ = ["mobile_companion_websocket_endpoint"]
