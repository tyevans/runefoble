"""Route helpers that MCP tools use to call the owning services.

Every upstream call goes through the shared `ServiceClient` from `runefoble_platform`. That
client sends the service credential (ADR-0015 e) and the trace context. The helpers here
build the routes, map upstream failures to tool errors, and never return a substitute value.
"""

from __future__ import annotations

import asyncio
import json
import weakref
from typing import Any, Literal
from uuid import UUID

from opentelemetry import trace
from opentelemetry.trace import SpanKind
from runefoble_platform.service_client import (
    ServiceClient,
    UpstreamFailureError,
    UpstreamReply,
    UpstreamUnavailableError,
    path,
)

from gateway_mcp.settings import GatewayMcpSettings, load_settings

TIMEOUT_SECONDS = 5.0

TokenType = Literal["pc", "monster", "npc", "obstacle"]
InitiatedBy = Literal["player", "the_watcher", "stand_in"]

_SERVICE_URL_FIELDS = {
    "board_state": "board_state_url",
    "character_sheet": "character_sheet_url",
    "game_session": "game_session_url",
    "rules_compendium": "rules_compendium_url",
    "the_watcher": "the_watcher_url",
}

# One shared client per event loop, service, base URL, and credential. The HTTP connections of a
# client belong to the loop that opened them, so a loop never reuses another loop's clients.
_shared_clients: weakref.WeakKeyDictionary[
    asyncio.AbstractEventLoop, dict[tuple[str, str, str], ServiceClient]
] = weakref.WeakKeyDictionary()


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


def _error_detail(body: bytes) -> str:
    """Return the service error detail, or the raw body when it is not JSON."""
    try:
        decoded = json.loads(body)
    except ValueError:
        return body.decode("utf-8", errors="replace")
    if isinstance(decoded, dict) and "detail" in decoded:
        return str(decoded["detail"])
    return str(decoded)


def _shared_client(service: str, base_url: str, credential: str) -> ServiceClient:
    """Return the shared client of the running event loop for one service, creating it on first use."""
    clients = _shared_clients.setdefault(asyncio.get_running_loop(), {})
    key = (service, base_url, credential)
    client = clients.get(key)
    if client is None:
        client = ServiceClient(service, base_url, credential)
        clients[key] = client
    return client


def _character_route(character_id: str, *segments: str) -> str:
    """Return the character_sheet route for a character id. A malformed id is refused."""
    try:
        canonical = str(UUID(character_id))
    except ValueError as exc:
        raise ServiceRejectedError(
            f"character_id must be a character UUID, got '{character_id}'"
        ) from exc
    return path("api", "v1", "characters", canonical, *segments)


class OwningServices:
    """Calls the public routes of the owning services for one MCP tool call.

    `bearer` is the MCP caller's Zitadel token, forwarded as is. Without a bearer the call
    sends no Authorization header. The upstream service decides whether that call is allowed.
    """

    def __init__(
        self, settings: GatewayMcpSettings | None = None, *, bearer: str | None = None
    ) -> None:
        """Read the upstream settings. Each tool call builds one instance."""
        self._settings = settings or load_settings()
        self._bearer = bearer

    async def _send(
        self,
        service: str,
        method: str,
        route: str,
        json_body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> UpstreamReply:
        """Send one call through the shared client, inside a client span, and map failures."""
        base_url = getattr(self._settings, _SERVICE_URL_FIELDS[service])
        client = _shared_client(
            service, base_url, self._settings.service_credential.get_secret_value()
        )
        authorization = f"Bearer {self._bearer}" if self._bearer else None
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span(
            f"{service} {method}", kind=SpanKind.CLIENT, attributes={"peer.service": service}
        ):
            try:
                reply = await client.send(
                    method,
                    route,
                    authorization=authorization,
                    timeout_s=TIMEOUT_SECONDS,
                    json=json_body,
                    params=params,
                )
            except UpstreamUnavailableError as exc:
                raise ServiceUnavailableError(
                    f"{service} is unreachable at {base_url}: {exc.reason}"
                ) from exc
            except UpstreamFailureError as exc:
                raise ServiceUnavailableError(
                    f"{service} returned {exc.status_code}: {_error_detail(exc.body)}"
                ) from exc

        if reply.status_code >= 400:
            raise ServiceRejectedError(
                f"{service} rejected the request ({reply.status_code}): "
                f"{_error_detail(reply.body)}",
                status_code=reply.status_code,
            )
        return reply

    async def _json(
        self,
        service: str,
        method: str,
        route: str,
        json_body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send one call and decode its 2xx JSON object. A body that is not an object is an error."""
        reply = await self._send(service, method, route, json_body, params)
        try:
            decoded = json.loads(reply.body)
        except ValueError as exc:
            raise ServiceUnavailableError(f"{service} returned a body that is not JSON") from exc
        if not isinstance(decoded, dict):
            raise ServiceUnavailableError(f"{service} returned a JSON value that is not an object")
        return decoded

    async def create_board(
        self, *, session_id: str, campaign_id: str | None, cols: int, rows: int
    ) -> dict[str, Any]:
        """Create the board for a session. The caller checks first that the session has none.

        board_state refuses a request with no campaign and a caller who cannot run the campaign.
        """
        return await self._json(
            "board_state",
            "POST",
            path("api", "v1", "boards"),
            {"session_id": session_id, "campaign_id": campaign_id, "cols": cols, "rows": rows},
        )

    async def get_board(self, session_id: str) -> dict[str, Any]:
        """Read the board state for a session."""
        return await self._json("board_state", "GET", path("api", "v1", "boards", session_id))

    async def get_session(self, session_id: str) -> dict[str, Any]:
        """Read the stored game session state from game_session."""
        return await self._json("game_session", "GET", path("api", "v1", "sessions", session_id))

    async def start_combat(
        self, session_id: str, *, combatants: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Start a combat encounter in a game session and return its combat state."""
        return await self._json(
            "game_session",
            "POST",
            path("api", "v1", "sessions", session_id, "combat", "start"),
            {"combatants": combatants},
        )

    async def get_combat_state(self, session_id: str) -> dict[str, Any]:
        """Read the combat round, active combatant, and initiative order from game_session."""
        return await self._json(
            "game_session", "GET", path("api", "v1", "sessions", session_id, "combat")
        )

    async def get_character(self, character_id: str) -> dict[str, Any]:
        """Read the stored character sheet from character_sheet."""
        return await self._json("character_sheet", "GET", _character_route(character_id))

    async def change_health(self, character_id: str, *, delta: int, source: str) -> dict[str, Any]:
        """Apply damage (negative delta) or healing and return the stored sheet."""
        return await self._json(
            "character_sheet",
            "POST",
            _character_route(character_id, "health"),
            {"delta": delta, "source": source},
        )

    async def apply_penalty(
        self, character_id: str, *, penalty_type: str, description: str
    ) -> dict[str, Any]:
        """Impose a session miss penalty and return the stored sheet."""
        return await self._json(
            "character_sheet",
            "POST",
            _character_route(character_id, "penalties"),
            {
                "penalty_type": penalty_type,
                "description": description,
                "imposed_by": "the_watcher",
            },
        )

    async def cast_spell(
        self, character_id: str, *, spell_name: str, slot_level: int
    ) -> dict[str, Any]:
        """Cast a spell from a slot and return the stored sheet."""
        return await self._json(
            "character_sheet",
            "POST",
            _character_route(character_id, "spells", "cast"),
            {"spell_name": spell_name, "slot_level": slot_level},
        )

    async def apply_condition(
        self,
        character_id: str,
        *,
        condition: str,
        duration_rounds: int | None,
        source: str,
    ) -> dict[str, Any]:
        """Impose a status condition and return the stored sheet."""
        return await self._json(
            "character_sheet",
            "POST",
            _character_route(character_id, "conditions"),
            {"condition": condition, "duration_rounds": duration_rounds, "source": source},
        )

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
        return await self._json(
            "board_state",
            "POST",
            path("api", "v1", "boards", session_id, "tokens"),
            {
                "name": name,
                "token_type": token_type,
                "x": x,
                "y": y,
                "hp": hp,
                "is_friendly": is_friendly,
            },
        )

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
        return await self._json(
            "board_state",
            "POST",
            path("api", "v1", "boards", session_id, "tokens", token_id, "move"),
            {"to_x": to_x, "to_y": to_y, "initiated_by": initiated_by},
        )

    async def get_monster(self, name: str, *, campaign_id: str | None = None) -> dict[str, Any]:
        """Read a monster stat block from rules_compendium. `campaign_id` adds that campaign's homebrew."""
        params = {"campaign_id": campaign_id} if campaign_id else None
        return await self._json(
            "rules_compendium",
            "GET",
            path("api", "v1", "compendium", "monsters", name),
            params=params,
        )

    async def narrate(self, request: dict[str, Any]) -> dict[str, Any]:
        """Ask The Watcher for DM narration. The response is returned as The Watcher sent it."""
        return await self._json(
            "the_watcher", "POST", path("api", "v1", "watcher", "narrate"), request
        )

    async def propose_action(self, request: dict[str, Any]) -> dict[str, Any]:
        """Propose an agent action to The Watcher. The DM can veto it before it takes effect."""
        return await self._json(
            "the_watcher", "POST", path("api", "v1", "watcher", "actions", "propose"), request
        )

    async def balance_encounter(
        self, party_levels: list[int], target_difficulty: str
    ) -> dict[str, Any]:
        """Ask rules_compendium to balance an encounter for a party."""
        return await self._json(
            "rules_compendium",
            "POST",
            path("api", "v1", "compendium", "encounters", "balance"),
            {"party_levels": party_levels, "target_difficulty": target_difficulty},
        )
