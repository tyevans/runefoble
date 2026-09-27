"""Real-time WebSocket Zanzibar Permission Enforcement.

Enforces fine-grained SpiceDB Zanzibar authorization checks on active
WebSocket connections and incoming mutative actions (ADR-0001, Hard Invariant 1).
"""

from __future__ import annotations

import logging
from typing import Any

from gateway_api.auth import get_spicedb_client
from runefoble_auth.spicedb import SpiceDBClient

logger = logging.getLogger("runefoble.gateway.websocket_validator")

MOVE_ACTIONS = (
    "move_token",
    "board_move",
    "ghost_preview",
    "preview_intent",
    "confirm_intent",
    "cancel_preview",
)
HEALTH_ACTIONS = ("modify_hp", "apply_condition", "clear_condition")
DM_ACTIONS = ("spawn_monster", "set_scene", "spawn_encounter", "advance_turn", "end_session")
DOOR_ACTIONS = ("toggle_door", "door_toggled", "open_door", "close_door")
LIGHT_ACTIONS = ("place_light", "toggle_light", "light_placed")


def _extract_char_id(data: dict[str, Any]) -> str | None:
    return data.get("character_id") or data.get("characterId") or data.get("character")


class WebSocketActionValidator:
    """Validates real-time WebSocket actions against SpiceDB Zanzibar schema."""

    def __init__(self, spicedb_client: SpiceDBClient | None = None) -> None:
        self._spicedb = spicedb_client

    @property
    def spicedb(self) -> SpiceDBClient:
        return self._spicedb or get_spicedb_client()

    async def validate_connect(self, campaign_id: str, subject_id: str) -> bool:
        """Verify viewer/subject has campaign:view or campaign:read permission in SpiceDB."""
        for p in ("view", "read"):
            if await self.spicedb.check_permission("campaign", campaign_id, p, "user", subject_id):
                return True
        return False

    async def is_dungeon_master(self, campaign_id: str, subject_id: str) -> bool:
        """Check if subject holds DM or campaign management permissions."""
        for p in ("dungeon_master", "run_session", "owner"):
            if await self.spicedb.check_permission("campaign", campaign_id, p, "user", subject_id):
                return True
        return False

    async def _check_char_perm(self, char_id: str | None, subject_id: str) -> bool:
        if not char_id:
            return False
        for p in ("edit", "owner"):
            if await self.spicedb.check_permission(
                "character", str(char_id), p, "user", subject_id
            ):
                return True
        return False

    async def _validate_move_action(
        self, campaign_id: str, subject_id: str, data: dict[str, Any]
    ) -> bool:
        for p in ("move_token", "move"):
            if await self.spicedb.check_permission("campaign", campaign_id, p, "user", subject_id):
                return True
        tok = data.get("token_id") or data.get("tokenId")
        if tok and await self.spicedb.check_permission(
            "board_token", str(tok), "move", "user", subject_id
        ):
            return True
        return await self._check_char_perm(_extract_char_id(data), subject_id)

    async def _validate_health_action(
        self, campaign_id: str, subject_id: str, action: str, data: dict[str, Any]
    ) -> bool:
        if await self._check_char_perm(_extract_char_id(data), subject_id):
            return True
        for p in ("edit", "edit_character", action):
            if await self.spicedb.check_permission("campaign", campaign_id, p, "user", subject_id):
                return True
        return False

    async def validate_action(
        self, campaign_id: str, subject_id: str, action: str, data: dict[str, Any]
    ) -> bool:
        """Validate whether subject is authorized to perform action within campaign."""
        if await self.is_dungeon_master(campaign_id, subject_id):
            return True
        if action in MOVE_ACTIONS:
            return await self._validate_move_action(campaign_id, subject_id, data)
        if action in HEALTH_ACTIONS:
            return await self._validate_health_action(campaign_id, subject_id, action, data)
        if action in DOOR_ACTIONS or action in LIGHT_ACTIONS:
            for p in ("play", "run_session", "participate", "control", "move"):
                if await self.spicedb.check_permission(
                    "campaign", campaign_id, p, "user", subject_id
                ):
                    return True
            return False
        if action in DM_ACTIONS:
            return False
        return await self.spicedb.check_permission(
            "campaign", campaign_id, action, "user", subject_id
        )


default_action_validator = WebSocketActionValidator()

__all__ = [
    "DM_ACTIONS",
    "DOOR_ACTIONS",
    "HEALTH_ACTIONS",
    "LIGHT_ACTIONS",
    "MOVE_ACTIONS",
    "WebSocketActionValidator",
    "default_action_validator",
    "logger",
]
