"""Per-message permission rules of the board WebSocket (TASK-0547).

Each message type maps to one schema permission. A denied message raises `BoardActionDenied`.
The socket handler turns it into a protocol error and keeps the socket open.
"""

from __future__ import annotations

from typing import Any

from board_state.authz import (
    PLAY,
    VIEW,
    can_move_token,
    can_on_board,
    can_on_campaign,
)

CONFIRM_ACTIONS = ("confirm_move", "confirm_ghost", "confirm_intent")
TOKEN_ACTIONS = ("token_action", "radial_action")
PLAY_ACTIONS = ("aoe_place", "cast_spell", "spell_vfx", "SpellCast")


class BoardActionDenied(PermissionError):
    """Raised when the verified user lacks the permission that a message needs."""


async def authorize_message(
    user_id: str, session_id: str, action: str, is_cast: bool, data: dict[str, Any]
) -> None:
    """Raise `BoardActionDenied` unless the user may send this message type."""
    if action in CONFIRM_ACTIONS or action in TOKEN_ACTIONS:
        token_id = data.get("token_id")
        if token_id and not await can_move_token(user_id, session_id, str(token_id)):
            raise BoardActionDenied(f"'{action}' on token '{token_id}' needs board_token.move")
        return
    if is_cast or action in PLAY_ACTIONS:
        if not await can_on_campaign(user_id, session_id, PLAY):
            raise BoardActionDenied(f"'{action}' needs campaign.play")
        return
    if not await can_on_board(user_id, session_id, VIEW):
        raise BoardActionDenied(f"'{action}' needs board.view")
