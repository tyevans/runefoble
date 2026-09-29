"""Shared fixtures for game_session models test sub-suites."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from game_session.models import GameSessionState


class FakeJoinedEvent:
    """Mock joined event for testing player join transitions."""

    def __init__(self, character_id: UUID, player_id: str = "player-1") -> None:
        self.player_id = player_id
        self.character_id = character_id
        self.character_name = "Kaelen"
        self.character_class = "Ranger"


@pytest.fixture
def session_id() -> UUID:
    return uuid4()


@pytest.fixture
def campaign_id() -> UUID:
    return uuid4()


@pytest.fixture
def character_id() -> UUID:
    return uuid4()


@pytest.fixture
def initial_session_state(session_id: UUID, campaign_id: UUID) -> GameSessionState:
    return GameSessionState.initial(
        session_id=session_id,
        campaign_id=campaign_id,
        title="Tomb of the Star-Eater",
        dm_id="the_watcher",
    )
