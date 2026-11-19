"""Stream consumer that places the enemy tokens of a combat start (TASK-0749).

game_session records a combat start with its placements on one event. This consumer reads that
event from the session stream and places the tokens on the session board. It creates the board
first when the session has none.

Rules:
- The placements are checked in memory first. Only then are tokens bound and the board saved.
  A refused placement (off grid, occupied cell) saves nothing and raises. The message is then
  dead-lettered. The combat stays started.
- The board keeps the source event id in the same save. A redelivered event places nothing.
- Token ids come from the source event id and the placement index. A retry names the same tokens.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid5

from board_state.aggregate import BoardAggregate
from board_state.authz import bind_board_to_campaign, bind_token, board_campaign_id
from board_state.dependencies import BoardNotFoundError, get_board, repo
from board_state.events import save_and_publish
from board_state.models import BoardState
from runefoble_events.session import CombatEncounterStarted
from runefoble_platform.consumer_group import RedisConsumerGroup
from runefoble_platform.identifiers import opaque_aggregate_id
from runefoble_platform.redis_bus import RedisStreamsEventBus
from runefoble_platform.stream_consumer import StreamConsumer

SESSION_STREAM = "runefoble.events.session"
GROUP_NAME = "board_state_encounter_workers"
WORKER_NAME = "board_state_encounter_consumer_1"
TOKEN_NAMESPACE = UUID("6f0c1c7e-2b7e-4c1e-9a55-3d1f0b7e4a10")


class EncounterCampaignError(RuntimeError):
    """The combat start names a campaign that does not own the session board."""


class EncounterPlacementError(ValueError):
    """A placement is off the grid or on an occupied cell. Nothing is applied."""


def _check_placements(board: BoardState, placements: list[dict[str, Any]]) -> None:
    """Refuse the whole batch when one placement is off the grid or on an occupied cell."""
    occupied = {(token.x, token.y) for token in board.tokens.values()}
    for placement in placements:
        cell = (placement["x"], placement["y"])
        if not (0 <= cell[0] < board.cols and 0 <= cell[1] < board.rows):
            raise EncounterPlacementError(
                f"Placement {placement['name']} is off the grid at {cell}"
            )
        if cell in occupied:
            raise EncounterPlacementError(
                f"Placement {placement['name']} is on an occupied cell {cell}"
            )
        occupied.add(cell)


async def _board_for_encounter(event: CombatEncounterStarted) -> BoardAggregate:
    """Return the session board. Create it with the encounter grid when the session has none."""
    session_id = str(event.session_id)
    try:
        return await get_board(session_id)
    except BoardNotFoundError:
        pass
    if event.board_cols is None or event.board_rows is None:
        raise EncounterPlacementError("The combat start has no encounter grid size")
    board = BoardAggregate(opaque_aggregate_id(session_id, field="sess_id"))
    board.initialize_grid(cols=event.board_cols, rows=event.board_rows, session_id=session_id)
    await repo.save(board)
    await bind_board_to_campaign(session_id, str(event.campaign_id))
    return board


async def apply_encounter_event(event: Any, bus: RedisStreamsEventBus | None) -> None:
    """Place the tokens of one combat start on the session board, once."""
    if not isinstance(event, CombatEncounterStarted) or not event.placements:
        return
    session_id = str(event.session_id)
    campaign_id = str(event.campaign_id)
    board = await _board_for_encounter(event)
    source_event_id = str(event.event_id)
    if source_event_id in board.state.applied_encounter_event_ids:
        # A redelivery. These placements are already on the board.
        return
    owner = await board_campaign_id(session_id)
    if owner != campaign_id:
        raise EncounterCampaignError(
            f"Combat start {source_event_id} names campaign {campaign_id}, "
            f"not the campaign of board {session_id}."
        )
    _check_placements(board.state, event.placements)
    token_ids: list[str] = []
    for index, placement in enumerate(event.placements):
        token_id = str(uuid5(TOKEN_NAMESPACE, f"{source_event_id}:{index}"))
        board.place_token(
            token_id=token_id,
            name=placement["name"],
            token_type=placement["token_type"],
            x=placement["x"],
            y=placement["y"],
            hp=placement.get("hp"),
            is_friendly=bool(placement.get("is_friendly", False)),
        )
        token_ids.append(token_id)
    for token_id in token_ids:
        await bind_token(session_id, token_id, None, event.initiated_by, "monster")
    board.record_encounter_applied(source_event_id, token_ids)
    await save_and_publish(repo, board, bus)


def build_encounter_consumer(
    consumer_group: RedisConsumerGroup, bus: RedisStreamsEventBus
) -> StreamConsumer:
    """Build the stream consumer for combat starts on the session stream. The caller starts it."""

    async def _handle(_message_id: str, event: Any) -> None:
        await apply_encounter_event(event, bus)

    return StreamConsumer(
        consumer_group=consumer_group,
        stream=SESSION_STREAM,
        group_name=GROUP_NAME,
        consumer_name=WORKER_NAME,
        handler=_handle,
    )
