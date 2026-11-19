"""Aggregate repositories of the play package (ADR-0021 D6 rule 5).

The app container holds one `PlayRepositories`. Routes read it through `play_repositories`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from game_session.aggregate import GameSessionAggregate
from game_session.events import SessionEventPublisher
from game_session.shared.container_access import app_container
from runefoble_platform.event_bus import EventBusProvider
from runefoble_platform.event_sourcing import AggregateRepository, create_aggregate_repository
from starlette.requests import HTTPConnection


@dataclass(frozen=True)
class PlayRepositories:
    sessions: AggregateRepository[GameSessionAggregate]


def build_play_repositories(event_bus: EventBusProvider) -> PlayRepositories:
    """Build the play repositories. A saved session event is published on `event_bus`."""
    return PlayRepositories(
        sessions=create_aggregate_repository(
            GameSessionAggregate, event_bus=SessionEventPublisher(event_bus.get)
        ),
    )


def play_repositories(conn: HTTPConnection) -> PlayRepositories:
    """Return the play repositories of the app container."""
    return app_container(conn).play


def session_repository(conn: HTTPConnection) -> AggregateRepository[GameSessionAggregate]:
    """Return the game session repository of the app container."""
    return play_repositories(conn).sessions


PlayRepos = Annotated[PlayRepositories, Depends(play_repositories)]
SessionRepo = Annotated[AggregateRepository[GameSessionAggregate], Depends(session_repository)]

__all__ = [
    "PlayRepos",
    "PlayRepositories",
    "SessionRepo",
    "build_play_repositories",
    "play_repositories",
    "session_repository",
]
