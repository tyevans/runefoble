"""Typed owner routes: one function per public route of an owning bounded context.

Each function returns the method and path of one owner route. Both gateways call these
functions, so a route has one definition. The caller supplies the body and the query.
Path segments are encoded by `path()`, so a client value cannot change the route.
"""

from __future__ import annotations

from typing import NamedTuple

from runefoble_platform.service_client.paths import path


class OwnerRoute(NamedTuple):
    """The HTTP method and the absolute path of one owner route."""

    method: str
    path: str


def _character(character_id: str, *segments: str) -> str:
    return path("api", "v1", "characters", character_id, *segments)


# game_session


def get_campaign(campaign_id: str) -> OwnerRoute:
    """GET: one campaign. The owner checks `view`."""
    return OwnerRoute("GET", path("api", "v1", "campaigns", campaign_id))


# character_sheet


def get_character(character_id: str) -> OwnerRoute:
    """GET: the stored character sheet."""
    return OwnerRoute("GET", _character(character_id))


def change_health(character_id: str) -> OwnerRoute:
    """POST: apply damage (negative delta) or healing."""
    return OwnerRoute("POST", _character(character_id, "health"))


def apply_penalty(character_id: str) -> OwnerRoute:
    """POST: impose a session miss penalty."""
    return OwnerRoute("POST", _character(character_id, "penalties"))


def apply_condition(character_id: str) -> OwnerRoute:
    """POST: impose a tactical status condition."""
    return OwnerRoute("POST", _character(character_id, "conditions"))


def cast_spell(character_id: str) -> OwnerRoute:
    """POST: cast a spell from a slot."""
    return OwnerRoute("POST", _character(character_id, "spells", "cast"))


# board_state


def get_token(session_id: str, token_id: str) -> OwnerRoute:
    """GET: one placed token of a session's board."""
    return OwnerRoute("GET", path("api", "v1", "boards", session_id, "tokens", token_id))


def place_token(session_id: str) -> OwnerRoute:
    """POST: place a token on the board of a session."""
    return OwnerRoute("POST", path("api", "v1", "boards", session_id, "tokens"))


def move_token(session_id: str, token_id: str) -> OwnerRoute:
    """POST: move a token on the board."""
    return OwnerRoute("POST", path("api", "v1", "boards", session_id, "tokens", token_id, "move"))


# rules_compendium


def get_monster(name: str) -> OwnerRoute:
    """GET: a monster stat block by name."""
    return OwnerRoute("GET", path("api", "v1", "compendium", "monsters", name))


def balance_encounter() -> OwnerRoute:
    """POST: balance an encounter for a party."""
    return OwnerRoute("POST", path("api", "v1", "compendium", "encounters", "balance"))
