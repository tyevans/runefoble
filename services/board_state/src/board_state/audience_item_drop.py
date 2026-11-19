"""Places an approved audience item drop on the board of its session as a loot token (TASK-0837).

Governed by ADR-0006 (Redis Streams event bus), ADR-0007 (each owner applies its own effect),
ADR-0011 (state changes go through the BoardState aggregate), and ADR-0015 (fail loud).
Only `item_drop` modifiers that the DM approved are applied here. A handler that raises routes
the message to the dead-letter stream, and nothing is applied then.
"""

from __future__ import annotations

from typing import Any

from board_state.authz import board_campaign_id
from board_state.dependencies import get_board, repo
from board_state.events import save_and_publish
from runefoble_events.events import AudienceModifierApproved
from runefoble_platform.audience_modifiers import (
    approved_modifier,
    integer_parameter,
    refusal,
    require_same_campaign,
    text_parameter,
)
from runefoble_platform.redis_bus import RedisStreamsEventBus

ITEM_DROP_MODIFIER = "item_drop"
LOOT_TOKEN_TYPE = "loot"


def _optional_item_id(modifier: AudienceModifierApproved) -> None:
    """Refuse an `item_id` that is present but is not text. The id is not stored yet."""
    if modifier.parameters.get("item_id") is not None:
        text_parameter(modifier, "item_id")


async def apply_audience_item_drop_event(event: Any, bus: RedisStreamsEventBus | None) -> None:
    """Place the approved item on the board of the modifier's session as a loot token.

    A rejected proposal and any other modifier type are ignored. The board must exist and must
    belong to the campaign of the modifier. The cell must lie on the grid and must not hold a
    token. The loot token takes the proposal id as its token id, so a redelivery places nothing.
    """
    modifier = approved_modifier(event, ITEM_DROP_MODIFIER)
    if modifier is None:
        return
    if modifier.session_id is None:
        raise refusal(modifier, "has no session.")
    session_id = str(modifier.session_id)
    x = integer_parameter(modifier, "x")
    y = integer_parameter(modifier, "y")
    item_name = text_parameter(modifier, "item_name")
    _optional_item_id(modifier)

    board = await get_board(session_id)
    owner = await board_campaign_id(session_id)
    require_same_campaign(modifier, owner, f"board {session_id}")
    token_id = str(modifier.proposal_id)
    if token_id in board.state.tokens:
        # A redelivery. The loot token of this proposal is already on the board.
        return
    if any(tok.x == x and tok.y == y for tok in board.state.tokens.values()):
        raise refusal(modifier, f"targets cell ({x}, {y}) that already holds a token.")
    board.place_token(
        token_id=token_id,
        name=item_name,
        token_type=LOOT_TOKEN_TYPE,
        x=x,
        y=y,
    )
    await save_and_publish(repo, board, bus)
