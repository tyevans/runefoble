"""Redis Streams consumer that places an approved audience hazard on the board of its session (TASK-0835).

Governed by ADR-0006 (Redis Streams event bus), ADR-0007 (each owner applies its own effect),
ADR-0011 (state changes go through the BoardState aggregate), and ADR-0015 (fail loud).
Only `hazard_spawn` modifiers that the DM approved are applied here. A handler that raises
routes the message to the dead-letter stream, and nothing is applied then.
"""

from __future__ import annotations

from typing import Any

from board_state.authz import board_campaign_id
from board_state.dependencies import get_board, repo
from board_state.events import save_and_publish
from board_state.rules.hazards import is_known_hazard
from runefoble_events.events import AudienceModifierApproved
from runefoble_platform.consumer_group import RedisConsumerGroup
from runefoble_platform.redis_bus import RedisStreamsEventBus
from runefoble_platform.stream_consumer import StreamConsumer

GROUP_NAME = "board_state_audience_workers"
WORKER_NAME = "board_state_audience_consumer_1"
AUDIENCE_STREAM = "runefoble.events.audience"
HAZARD_MODIFIER = "hazard_spawn"


class AudienceHazardError(RuntimeError):
    """Raised when an approved hazard modifier cannot be placed on its board."""


def _integer_parameter(parameters: dict[str, Any], name: str, proposal_id: Any) -> int:
    value = parameters.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise AudienceHazardError(
            f"Approved hazard modifier {proposal_id} needs an integer '{name}' parameter."
        )
    return value


def _hazard_type_parameter(parameters: dict[str, Any], proposal_id: Any) -> str:
    value = parameters.get("hazard_type")
    if not isinstance(value, str) or not value.strip():
        raise AudienceHazardError(
            f"Approved hazard modifier {proposal_id} needs a 'hazard_type' parameter."
        )
    if not is_known_hazard(value):
        raise AudienceHazardError(
            f"Approved hazard modifier {proposal_id} names an unknown hazard type '{value}'."
        )
    return value


async def apply_audience_hazard_event(event: Any, bus: RedisStreamsEventBus | None) -> None:
    """Place the approved hazard on the board of the modifier's session.

    A rejected proposal (`approved` is not true) and any other modifier type are ignored.
    The board must exist and must belong to the campaign of the modifier. The cell must lie on
    the grid. The cell keeps its elevation and terrain type, and gains the hazard.
    """
    if not isinstance(event, AudienceModifierApproved):
        return
    if event.approved is not True or event.modifier_type != HAZARD_MODIFIER:
        return
    if event.session_id is None:
        raise AudienceHazardError(f"Approved hazard modifier {event.proposal_id} has no session.")
    session_id = str(event.session_id)
    x = _integer_parameter(event.parameters, "x", event.proposal_id)
    y = _integer_parameter(event.parameters, "y", event.proposal_id)
    hazard_type = _hazard_type_parameter(event.parameters, event.proposal_id)

    board = await get_board(session_id)
    owner = await board_campaign_id(session_id)
    if owner != str(event.campaign_id):
        raise AudienceHazardError(
            f"Approved hazard modifier {event.proposal_id} belongs to campaign {event.campaign_id}, "
            f"not to the campaign of board {session_id}."
        )
    current = board.get_terrain(x, y)
    board.configure_terrain(
        x=x,
        y=y,
        elevation=current.elevation,
        terrain_type=current.terrain_type,
        hazard=hazard_type,
    )
    await save_and_publish(repo, board, bus)


def build_audience_hazard_consumer(
    consumer_group: RedisConsumerGroup, bus: RedisStreamsEventBus
) -> StreamConsumer:
    """Build the stream consumer for the audience stream. The caller starts it."""

    async def _handle(_message_id: str, event: Any) -> None:
        await apply_audience_hazard_event(event, bus)

    return StreamConsumer(
        consumer_group=consumer_group,
        stream=AUDIENCE_STREAM,
        group_name=GROUP_NAME,
        consumer_name=WORKER_NAME,
        handler=_handle,
    )
