"""Typed owner routes: one function per public route of an owning bounded context.

Each function returns the method and path of one owner route. The MCP gateway and the API
gateway call these functions, so a route has one definition. The caller supplies the body and
the query. Path segments are encoded by `path()`, so a client value cannot change the route.
A value the owner path cannot encode (`.`, `..`, or empty) raises ValueError.
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


def _session(session_id: str, *segments: str) -> str:
    return path("api", "v1", "sessions", session_id, *segments)


# game_session


def get_campaign(campaign_id: str) -> OwnerRoute:
    """GET: one campaign. The owner checks `view`."""
    return OwnerRoute("GET", path("api", "v1", "campaigns", campaign_id))


def get_session(session_id: str) -> OwnerRoute:
    """GET: the stored game session state, participants, and turn index."""
    return OwnerRoute("GET", _session(session_id))


def join_session(session_id: str) -> OwnerRoute:
    """POST: seat the verified caller in the lobby. The owner checks `participate`."""
    return OwnerRoute("POST", _session(session_id, "join"))


def start_encounter(session_id: str) -> OwnerRoute:
    """POST: start combat and record the enemy placements on one event. The owner checks `control`."""
    return OwnerRoute("POST", _session(session_id, "encounters", "start"))


def get_combat_state(session_id: str) -> OwnerRoute:
    """GET: the combat round, active combatant, and initiative order of a session."""
    return OwnerRoute("GET", _session(session_id, "combat"))


def end_session(session_id: str) -> OwnerRoute:
    """POST: end a session. The owner checks `control`."""
    return OwnerRoute("POST", _session(session_id, "end"))


# character_sheet


def list_characters() -> OwnerRoute:
    """GET: the characters the caller may view. The caller adds the campaign filter."""
    return OwnerRoute("GET", path("api", "v1", "characters"))


def create_character() -> OwnerRoute:
    """POST: create a character. The owner records the caller as its owner."""
    return OwnerRoute("POST", path("api", "v1", "characters"))


def get_character(character_id: str) -> OwnerRoute:
    """GET: the stored character sheet."""
    return OwnerRoute("GET", _character(character_id))


def assign_campaign(character_id: str) -> OwnerRoute:
    """PATCH: assign or unassign the campaign of a character."""
    return OwnerRoute("PATCH", _character(character_id, "campaign"))


def change_health(character_id: str) -> OwnerRoute:
    """POST: apply damage (negative delta) or healing."""
    return OwnerRoute("POST", _character(character_id, "health"))


def apply_penalty(character_id: str) -> OwnerRoute:
    """POST: impose a session miss penalty."""
    return OwnerRoute("POST", _character(character_id, "penalties"))


def apply_condition(character_id: str) -> OwnerRoute:
    """POST: impose a tactical status condition."""
    return OwnerRoute("POST", _character(character_id, "conditions"))


def remove_condition(character_id: str, condition: str) -> OwnerRoute:
    """DELETE: clear one tactical status condition."""
    return OwnerRoute("DELETE", _character(character_id, "conditions", condition))


def cast_spell(character_id: str) -> OwnerRoute:
    """POST: cast a spell from a slot."""
    return OwnerRoute("POST", _character(character_id, "spells", "cast"))


def prepare_spell(character_id: str) -> OwnerRoute:
    """POST: prepare or unprepare a spell."""
    return OwnerRoute("POST", _character(character_id, "spells", "prepare"))


def equip_item(character_id: str) -> OwnerRoute:
    """POST: equip an item into a slot."""
    return OwnerRoute("POST", _character(character_id, "equipment"))


def unequip_item(character_id: str, slot: str) -> OwnerRoute:
    """DELETE: clear one equipment slot."""
    return OwnerRoute("DELETE", _character(character_id, "equipment", slot))


def add_inventory_item(character_id: str) -> OwnerRoute:
    """POST: add an item to the inventory."""
    return OwnerRoute("POST", _character(character_id, "inventory"))


def remove_inventory_item(character_id: str, item_id: str) -> OwnerRoute:
    """DELETE: remove or decrement one inventory item."""
    return OwnerRoute("DELETE", _character(character_id, "inventory", item_id))


def get_guardrails(character_id: str) -> OwnerRoute:
    """GET: the stand-in guardrails of a character."""
    return OwnerRoute("GET", _character(character_id, "guardrails"))


def update_guardrails(character_id: str) -> OwnerRoute:
    """PUT: store the stand-in guardrails of a character."""
    return OwnerRoute("PUT", _character(character_id, "guardrails"))


def clear_condition(character_id: str, condition: str) -> OwnerRoute:
    """DELETE: remove one tactical status condition."""
    return OwnerRoute("DELETE", _character(character_id, "conditions", condition))


# board_state


def create_board() -> OwnerRoute:
    """POST: create the board of a session. The owner checks `campaign.run_session`."""
    return OwnerRoute("POST", path("api", "v1", "boards"))


def get_board(session_id: str) -> OwnerRoute:
    """GET: the board state of a session."""
    return OwnerRoute("GET", path("api", "v1", "boards", session_id))


def get_token(session_id: str, token_id: str) -> OwnerRoute:
    """GET: one placed token of a session's board."""
    return OwnerRoute("GET", path("api", "v1", "boards", session_id, "tokens", token_id))


def place_token(session_id: str) -> OwnerRoute:
    """POST: place a token on the board of a session. The owner checks the token permissions."""
    return OwnerRoute("POST", path("api", "v1", "boards", session_id, "tokens"))


def move_token(session_id: str, token_id: str) -> OwnerRoute:
    """POST: move a token on the board."""
    return OwnerRoute("POST", path("api", "v1", "boards", session_id, "tokens", token_id, "move"))


# the_watcher


def narrate() -> OwnerRoute:
    """POST: ask The Watcher for DM narration and rulings."""
    return OwnerRoute("POST", path("api", "v1", "watcher", "narrate"))


def propose_action() -> OwnerRoute:
    """POST: propose an agent action to The Watcher. The DM can veto it."""
    return OwnerRoute("POST", path("api", "v1", "watcher", "actions", "propose"))


def toggle_door(board_id: str, door_id: str) -> OwnerRoute:
    """POST: toggle one interactive door or portal. The owner checks `play`."""
    return OwnerRoute("POST", path("api", "v1", "boards", board_id, "doors", door_id, "toggle"))


def place_light(board_id: str) -> OwnerRoute:
    """POST: place or update a dynamic light. The owner checks `manage_traps`."""
    return OwnerRoute("POST", path("api", "v1", "boards", board_id, "lights"))


# rules_compendium


def get_monster(name: str) -> OwnerRoute:
    """GET: a monster stat block by name."""
    return OwnerRoute("GET", path("api", "v1", "compendium", "monsters", name))


def balance_encounter() -> OwnerRoute:
    """POST: balance an encounter for a party."""
    return OwnerRoute("POST", path("api", "v1", "compendium", "encounters", "balance"))
