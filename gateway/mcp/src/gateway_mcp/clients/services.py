"""Typed async HTTP client for the owning services behind MCP tools.

Every call goes through a public service route. The client never returns
fallback data. Upstream failures raise a ServiceError, which FastMCP reports
to the caller as an MCP tool error result.
"""

from __future__ import annotations

from typing import Any, Literal
from urllib.parse import quote
from uuid import UUID

import httpx
from gateway_mcp.settings import GatewayMcpSettings, load_settings
from runefoble_platform.service_credential import SERVICE_CREDENTIAL_HEADER

DEFAULT_TIMEOUT_SECONDS = 5.0

TokenType = Literal["pc", "monster", "npc", "obstacle"]
InitiatedBy = Literal["player", "the_watcher", "stand_in"]


class ServiceError(Exception):
    """Base error for a failed call to an owning service."""


class ServiceUnavailableError(ServiceError):
    """The service could not be reached, or it answered with a 5xx status."""


class ServiceRejectedError(ServiceError):
    """The service refused the request with a 4xx status."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Keep the refusing HTTP status so callers can tell a missing resource from a bad request."""
        super().__init__(message)
        self.status_code = status_code


def _error_detail(response: httpx.Response) -> str:
    """Return the service error detail, or the raw body when it is not JSON."""
    try:
        body = response.json()
    except ValueError:
        return response.text
    if isinstance(body, dict) and "detail" in body:
        return str(body["detail"])
    return str(body)


def _character_path(character_id: str) -> str:
    """Return the character_sheet route for a character id, or reject a malformed id."""
    try:
        return f"/api/v1/characters/{UUID(character_id)}"
    except ValueError as exc:
        raise ServiceRejectedError(
            f"character_id must be a character UUID, got '{character_id}'"
        ) from exc


class ServiceClient:
    """Calls the board_state, character_sheet, game_session, and rules_compendium public routes."""

    def __init__(
        self, settings: GatewayMcpSettings | None = None, *, bearer: str | None = None
    ) -> None:
        """Create a client. `bearer` is the MCP caller's Zitadel token, forwarded as is.

        Without a bearer the client sends no Authorization header. The upstream service
        decides whether that request is allowed.
        """
        self._settings = settings or load_settings()
        self._bearer = bearer
        self._service_credential = self._settings.service_credential.get_secret_value()

    async def _request(
        self,
        service: str,
        base_url: str,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        # The service credential goes on every call (ADR-0015 e). The user bearer, when the MCP
        # caller has one, goes on as is, so the owning service acts for that user (ADR-0015 c).
        headers = {SERVICE_CREDENTIAL_HEADER: self._service_credential}
        if self._bearer:
            headers["Authorization"] = f"Bearer {self._bearer}"
        try:
            async with httpx.AsyncClient(
                base_url=base_url, timeout=DEFAULT_TIMEOUT_SECONDS
            ) as http:
                response = await http.request(method, path, json=json_body, headers=headers)
        except httpx.HTTPError as exc:
            raise ServiceUnavailableError(f"{service} is unreachable at {base_url}: {exc}") from exc

        if response.status_code >= 500:
            raise ServiceUnavailableError(
                f"{service} returned {response.status_code}: {_error_detail(response)}"
            )
        if response.status_code >= 400:
            raise ServiceRejectedError(
                f"{service} rejected the request ({response.status_code}): "
                f"{_error_detail(response)}",
                status_code=response.status_code,
            )
        return response.json()

    async def create_board(
        self, *, session_id: str, campaign_id: str | None, cols: int, rows: int
    ) -> dict[str, Any]:
        """Create the board for a session. The caller checks first that the session has none.

        board_state refuses a request with no campaign and a caller who cannot run the campaign.
        """
        result = await self._request(
            "board_state",
            self._settings.board_state_url,
            "POST",
            "/api/v1/boards",
            {"session_id": session_id, "campaign_id": campaign_id, "cols": cols, "rows": rows},
        )
        return dict(result)

    async def get_board(self, session_id: str) -> dict[str, Any]:
        """Read the board state for a session."""
        result = await self._request(
            "board_state",
            self._settings.board_state_url,
            "GET",
            f"/api/v1/boards/{session_id}",
        )
        return dict(result)

    async def get_session(self, session_id: str) -> dict[str, Any]:
        """Read the stored game session state from game_session."""
        result = await self._request(
            "game_session",
            self._settings.game_session_url,
            "GET",
            f"/api/v1/sessions/{quote(session_id, safe='')}",
        )
        return dict(result)

    async def start_combat(
        self, session_id: str, *, combatants: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Start a combat encounter in a game session and return its combat state."""
        result = await self._request(
            "game_session",
            self._settings.game_session_url,
            "POST",
            f"/api/v1/sessions/{quote(session_id, safe='')}/combat/start",
            {"combatants": combatants},
        )
        return dict(result)

    async def get_combat_state(self, session_id: str) -> dict[str, Any]:
        """Read the combat round, active combatant, and initiative order from game_session."""
        result = await self._request(
            "game_session",
            self._settings.game_session_url,
            "GET",
            f"/api/v1/sessions/{session_id}/combat",
        )
        return dict(result)

    async def get_character(self, character_id: str) -> dict[str, Any]:
        """Read the stored character sheet from character_sheet."""
        result = await self._request(
            "character_sheet",
            self._settings.character_sheet_url,
            "GET",
            _character_path(character_id),
        )
        return dict(result)

    async def change_health(self, character_id: str, *, delta: int, source: str) -> dict[str, Any]:
        """Apply damage (negative delta) or healing and return the stored sheet."""
        result = await self._request(
            "character_sheet",
            self._settings.character_sheet_url,
            "POST",
            f"{_character_path(character_id)}/health",
            {"delta": delta, "source": source},
        )
        return dict(result)

    async def apply_penalty(
        self, character_id: str, *, penalty_type: str, description: str
    ) -> dict[str, Any]:
        """Impose a session miss penalty and return the stored sheet."""
        result = await self._request(
            "character_sheet",
            self._settings.character_sheet_url,
            "POST",
            f"{_character_path(character_id)}/penalties",
            {
                "penalty_type": penalty_type,
                "description": description,
                "imposed_by": "the_watcher",
            },
        )
        return dict(result)

    async def cast_spell(
        self, character_id: str, *, spell_name: str, slot_level: int
    ) -> dict[str, Any]:
        """Cast a spell from a slot and return the stored sheet."""
        result = await self._request(
            "character_sheet",
            self._settings.character_sheet_url,
            "POST",
            f"{_character_path(character_id)}/spells/cast",
            {"spell_name": spell_name, "slot_level": slot_level},
        )
        return dict(result)

    async def apply_condition(
        self,
        character_id: str,
        *,
        condition: str,
        duration_rounds: int | None,
        source: str,
    ) -> dict[str, Any]:
        """Impose a status condition and return the stored sheet."""
        result = await self._request(
            "character_sheet",
            self._settings.character_sheet_url,
            "POST",
            f"{_character_path(character_id)}/conditions",
            {"condition": condition, "duration_rounds": duration_rounds, "source": source},
        )
        return dict(result)

    async def place_token(
        self,
        session_id: str,
        *,
        name: str,
        token_type: TokenType,
        x: int,
        y: int,
        hp: int | None,
        is_friendly: bool,
    ) -> dict[str, Any]:
        """Place a token on the board and return its stored state."""
        result = await self._request(
            "board_state",
            self._settings.board_state_url,
            "POST",
            f"/api/v1/boards/{session_id}/tokens",
            {
                "name": name,
                "token_type": token_type,
                "x": x,
                "y": y,
                "hp": hp,
                "is_friendly": is_friendly,
            },
        )
        return dict(result)

    async def move_token(
        self,
        session_id: str,
        token_id: str,
        *,
        to_x: int,
        to_y: int,
        initiated_by: InitiatedBy,
    ) -> dict[str, Any]:
        """Move a token and return the move result from the board."""
        result = await self._request(
            "board_state",
            self._settings.board_state_url,
            "POST",
            f"/api/v1/boards/{session_id}/tokens/{token_id}/move",
            {"to_x": to_x, "to_y": to_y, "initiated_by": initiated_by},
        )
        return dict(result)

    async def get_monster(self, name: str) -> dict[str, Any]:
        """Read a monster stat block from rules_compendium."""
        result = await self._request(
            "rules_compendium",
            self._settings.rules_compendium_url,
            "GET",
            f"/api/v1/compendium/monsters/{quote(name, safe='')}",
        )
        return dict(result)

    async def narrate(self, request: dict[str, Any]) -> dict[str, Any]:
        """Ask The Watcher for DM narration. The response is returned as The Watcher sent it."""
        result = await self._request(
            "the_watcher",
            self._settings.the_watcher_url,
            "POST",
            "/api/v1/watcher/narrate",
            request,
        )
        return dict(result)

    async def propose_action(self, request: dict[str, Any]) -> dict[str, Any]:
        """Propose an agent action to The Watcher. The DM can veto it before it takes effect."""
        result = await self._request(
            "the_watcher",
            self._settings.the_watcher_url,
            "POST",
            "/api/v1/watcher/actions/propose",
            request,
        )
        return dict(result)

    async def balance_encounter(
        self, party_levels: list[int], target_difficulty: str
    ) -> dict[str, Any]:
        """Ask rules_compendium to balance an encounter for a party."""
        result = await self._request(
            "rules_compendium",
            self._settings.rules_compendium_url,
            "POST",
            "/api/v1/compendium/encounters/balance",
            {"party_levels": party_levels, "target_difficulty": target_difficulty},
        )
        return dict(result)
