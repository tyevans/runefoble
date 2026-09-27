"""Mobile companion connection and session state management."""

from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket
from runefoble_events.voice import MobileHapticPingDispatched
from voice_agent.mobile import (
    HapticVibrationPattern,
    MobileAudioProfileTier,
    create_diegetic_whisper_notification,
    create_haptic_payload,
    create_turn_alert_notification,
)

logger = logging.getLogger("runefoble.gateway.companion.manager")


async def publish_companion_event(stream: str, event: Any) -> None:
    import gateway_api.main as gw_main

    if bus := gw_main.get_event_bus():
        with contextlib.suppress(Exception):
            await bus.publish_event(stream, event)


class MobileCompanionManager:
    """Manages active mobile companion WebSocket connections per session."""

    def __init__(self) -> None:
        self.active_companions: dict[str, dict[str, WebSocket]] = {}  # session_id -> user_id -> ws
        self.peer_sessions: dict[
            WebSocket, tuple[str, str, str]
        ] = {}  # ws -> (session_id, user_id, peer_id)
        self.active_profiles: dict[str, dict[str, str]] = {}  # session_id -> user_id -> tier

    async def connect(
        self, session_id: str, user_id: str, peer_id: str, websocket: WebSocket
    ) -> None:
        if session_id not in self.active_companions:
            self.active_companions[session_id] = {}
            self.active_profiles[session_id] = {}
        self.active_companions[session_id][user_id] = websocket
        self.active_profiles[session_id][user_id] = MobileAudioProfileTier.MOBILE_OPTIMIZED
        self.peer_sessions[websocket] = (session_id, user_id, peer_id)

    def disconnect(self, websocket: WebSocket) -> tuple[str, str, str] | None:
        info = self.peer_sessions.pop(websocket, None)
        if not info:
            return None
        session_id, user_id, _ = info
        if session_id in self.active_companions:
            self.active_companions[session_id].pop(user_id, None)
            if not self.active_companions[session_id]:
                del self.active_companions[session_id]
                self.active_profiles.pop(session_id, None)
        return info

    async def send_to_user(self, session_id: str, user_id: str, message: dict[str, Any]) -> bool:
        ws = self.active_companions.get(session_id, {}).get(user_id)
        if ws:
            with contextlib.suppress(Exception):
                await ws.send_json(message)
                return True
        return False

    async def broadcast_to_session(
        self, session_id: str, message: dict[str, Any], exclude_user: str | None = None
    ) -> None:
        users = list(self.active_companions.get(session_id, {}).items())
        for uid, ws in users:
            if uid != exclude_user:
                with contextlib.suppress(Exception):
                    await ws.send_json(message)

    async def dispatch_whisper(
        self,
        session_id: str,
        recipient_id: str,
        content: str,
        sender: str = "The Watcher",
        character_name: str | None = None,
    ) -> dict[str, Any]:
        """Dispatch a secret DM whisper accompanied by a triple-pulse haptic ping."""
        whisper_data = {
            "content": content,
            "sender": sender,
            "character_name": character_name,
            "recipient_id": recipient_id,
            "is_secret": True,
        }
        notification = create_diegetic_whisper_notification(
            content=content,
            sender=sender,
            character_name=character_name,
            is_secret=True,
        )
        haptic_frame = create_haptic_payload(
            session_id=session_id,
            alert_type="secret_whisper",
            custom_pattern=HapticVibrationPattern.SECRET_WHISPER,
            whisper=whisper_data,
            notification=notification,
            recipient_id=recipient_id,
        )
        await self.send_to_user(session_id, recipient_id, haptic_frame)

        event = MobileHapticPingDispatched(
            session_id=session_id,
            recipient_id=recipient_id,
            alert_type="secret_whisper",
            vibration_pattern=HapticVibrationPattern.SECRET_WHISPER,
            whisper_content=content,
            notification_title=notification["title"],
            notification_body=notification["body"],
            diegetic=True,
            dispatched_at=datetime.now(UTC).isoformat(),
        )
        await publish_companion_event("runefoble.events.voice", event)
        return haptic_frame

    async def dispatch_turn_alert(
        self,
        session_id: str,
        recipient_id: str,
        character_name: str,
        round_num: int | None = None,
    ) -> dict[str, Any]:
        """Dispatch a combat turn prompt accompanied by a double-pulse haptic ping."""
        notification = create_turn_alert_notification(
            character_name=character_name,
            round_num=round_num,
        )
        haptic_frame = create_haptic_payload(
            session_id=session_id,
            alert_type="turn_alert",
            custom_pattern=HapticVibrationPattern.TURN_ALERT,
            notification=notification,
            recipient_id=recipient_id,
        )
        await self.send_to_user(session_id, recipient_id, haptic_frame)

        event = MobileHapticPingDispatched(
            session_id=session_id,
            recipient_id=recipient_id,
            alert_type="turn_alert",
            vibration_pattern=HapticVibrationPattern.TURN_ALERT,
            whisper_content=None,
            notification_title=notification["title"],
            notification_body=notification["body"],
            diegetic=True,
            dispatched_at=datetime.now(UTC).isoformat(),
        )
        await publish_companion_event("runefoble.events.voice", event)
        return haptic_frame


mobile_companion_manager = MobileCompanionManager()

__all__ = [
    "MobileCompanionManager",
    "mobile_companion_manager",
    "publish_companion_event",
]
