"""Real-time WebSocket Zanzibar Permission Enforcement.

Enforces fine-grained SpiceDB Zanzibar authorization checks on active
WebSocket connections and incoming mutative actions (ADR-0001, Hard Invariant 1).
"""

from __future__ import annotations

import logging
from typing import Any

from gateway_api.auth import get_spicedb_client
from runefoble_auth.contract import ACTION_PERMISSIONS
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
KNOWN_ACTIONS = frozenset(MOVE_ACTIONS + HEALTH_ACTIONS + DM_ACTIONS + DOOR_ACTIONS + LIGHT_ACTIONS)


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
        """Verify the subject holds campaign.view in SpiceDB."""
        _, view = ACTION_PERMISSIONS["campaign.view"]
        return await self.spicedb.check_permission(
            "campaign", campaign_id, view, "user", subject_id
        )

    async def can_run_session(self, campaign_id: str, subject_id: str) -> bool:
        """Check if subject holds campaign.run_session (DM, GM, or owner) in SpiceDB."""
        _, run_session = ACTION_PERMISSIONS["campaign.run_session"]
        return await self.spicedb.check_permission(
            "campaign", campaign_id, run_session, "user", subject_id
        )

    async def _check_char_perm(self, char_id: str | None, subject_id: str) -> bool:
        if not char_id:
            return False
        _, edit = ACTION_PERMISSIONS["character.edit"]
        return await self.spicedb.check_permission(
            "character", str(char_id), edit, "user", subject_id
        )

    async def _validate_move_action(
        self, campaign_id: str, subject_id: str, data: dict[str, Any]
    ) -> bool:
        tok = data.get("token_id") or data.get("tokenId")
        if tok:
            _, move = ACTION_PERMISSIONS["board_token.move"]
            if await self.spicedb.check_permission(
                "board_token", str(tok), move, "user", subject_id
            ):
                return True
        return await self._check_char_perm(_extract_char_id(data), subject_id)

    async def _validate_health_action(
        self, campaign_id: str, subject_id: str, action: str, data: dict[str, Any]
    ) -> bool:
        # The DM check already ran in validate_action. Only the character editor remains.
        return await self._check_char_perm(_extract_char_id(data), subject_id)

    async def validate_action(
        self, campaign_id: str, subject_id: str, action: str, data: dict[str, Any]
    ) -> bool:
        """Validate whether subject is authorized to perform action within campaign."""
        if await self.can_run_session(campaign_id, subject_id):
            return True
        if action in MOVE_ACTIONS:
            return await self._validate_move_action(campaign_id, subject_id, data)
        if action in HEALTH_ACTIONS:
            return await self._validate_health_action(campaign_id, subject_id, action, data)
        if action in DOOR_ACTIONS or action in LIGHT_ACTIONS:
            _, play = ACTION_PERMISSIONS["campaign.play"]
            return await self.spicedb.check_permission(
                "campaign", campaign_id, play, "user", subject_id
            )
        return False


default_action_validator = WebSocketActionValidator()

__all__ = [
    "DM_ACTIONS",
    "DOOR_ACTIONS",
    "HEALTH_ACTIONS",
    "KNOWN_ACTIONS",
    "LIGHT_ACTIONS",
    "MOVE_ACTIONS",
    "WebSocketActionValidator",
    "default_action_validator",
    "logger",
]
