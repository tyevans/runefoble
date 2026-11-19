"""Route helpers that MCP tools use to call the owning services.

Every upstream call goes through the shared `ServiceClient` from `runefoble_platform`. That
client sends the service credential (ADR-0015 e) and the trace context. The helpers here
build the routes, map upstream failures to tool errors, and never return a substitute value.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

from opentelemetry import trace
from opentelemetry.trace import SpanKind
from runefoble_platform.service_client import (
    OWNER_URL_FIELDS,
    UpstreamFailureError,
    UpstreamReply,
    UpstreamUnavailableError,
    decode_json_body,
    error_detail,
    owner_routes,
)

from gateway_mcp.settings import GatewayMcpSettings, load_settings

if TYPE_CHECKING:
    from gateway_mcp.service_clients import ServiceClientPool

TIMEOUT_SECONDS = 5.0

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


def _canonical_character_id(character_id: str) -> str:
    """Return the canonical UUID of a character id. A malformed id is refused before any call."""
    try:
        return str(UUID(character_id))
    except ValueError as exc:
        raise ServiceRejectedError(
            f"character_id must be a character UUID, got '{character_id}'"
        ) from exc


class OwningServices:
    """Calls the public routes of the owning services for one MCP tool call.

    `clients` is the service client pool of the gateway container. `bearer` is the MCP
    caller's Zitadel token, forwarded as is. Without a bearer the call sends no Authorization
    header. The upstream service decides whether that call is allowed.
    """

    def __init__(
        self,
        clients: ServiceClientPool,
        settings: GatewayMcpSettings | None = None,
        *,
        bearer: str | None = None,
    ) -> None:
        """Read the upstream settings. Each tool call builds one instance."""
        self._clients = clients
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
        base_url = getattr(self._settings, OWNER_URL_FIELDS[service])
        client = self._clients.client(
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
                    f"{service} returned {exc.status_code}: {error_detail(exc.body)}"
                ) from exc

        if reply.status_code >= 400:
            raise ServiceRejectedError(
                f"{service} rejected the request ({reply.status_code}): {error_detail(reply.body)}",
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
            decoded = decode_json_body(reply.body)
        except ValueError as exc:
            raise ServiceUnavailableError(f"{service} returned a body that is not JSON") from exc
        if not isinstance(decoded, dict):
            raise ServiceUnavailableError(f"{service} returned a JSON value that is not an object")
        return decoded

    async def get_board(self, session_id: str) -> dict[str, Any]:
        """Read the board state for a session."""
        route = owner_routes.get_board(session_id)
        return await self._json("board_state", route.method, route.path)

    async def get_session(self, session_id: str) -> dict[str, Any]:
        """Read the stored game session state from game_session."""
        route = owner_routes.get_session(session_id)
        return await self._json("game_session", route.method, route.path)

    async def start_encounter(
        self, session_id: str, *, campaign_id: str | None, enemies: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Start combat and record the enemy placements in one game_session write.

        game_session reads each missing challenge rating from rules_compendium, with the
        homebrew monsters of `campaign_id`. board_state places the tokens later, from the
        session event. The reply holds the combat state and the placements that game_session
        accepted.
        """
        route = owner_routes.start_encounter(session_id)
        body: dict[str, Any] = {"enemies": enemies}
        if campaign_id is not None:
            body["campaign_id"] = campaign_id
        return await self._json("game_session", route.method, route.path, body)

    async def get_combat_state(self, session_id: str) -> dict[str, Any]:
        """Read the combat round, active combatant, and initiative order from game_session."""
        route = owner_routes.get_combat_state(session_id)
        return await self._json("game_session", route.method, route.path)

    async def get_character(self, character_id: str) -> dict[str, Any]:
        """Read the stored character sheet from character_sheet."""
        route = owner_routes.get_character(_canonical_character_id(character_id))
        return await self._json("character_sheet", route.method, route.path)

    async def change_health(self, character_id: str, *, delta: int, source: str) -> dict[str, Any]:
        """Apply damage (negative delta) or healing and return the stored sheet."""
        route = owner_routes.change_health(_canonical_character_id(character_id))
        return await self._json(
            "character_sheet", route.method, route.path, {"delta": delta, "source": source}
        )

    async def apply_penalty(
        self, character_id: str, *, penalty_type: str, description: str
    ) -> dict[str, Any]:
        """Impose a session miss penalty and return the stored sheet."""
        route = owner_routes.apply_penalty(_canonical_character_id(character_id))
        return await self._json(
            "character_sheet",
            route.method,
            route.path,
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
        route = owner_routes.cast_spell(_canonical_character_id(character_id))
        return await self._json(
            "character_sheet",
            route.method,
            route.path,
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
        route = owner_routes.apply_condition(_canonical_character_id(character_id))
        return await self._json(
            "character_sheet",
            route.method,
            route.path,
            {"condition": condition, "duration_rounds": duration_rounds, "source": source},
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
        route = owner_routes.move_token(session_id, token_id)
        return await self._json(
            "board_state",
            route.method,
            route.path,
            {"to_x": to_x, "to_y": to_y, "initiated_by": initiated_by},
        )

    async def get_monster(self, name: str) -> dict[str, Any]:
        """Read a monster stat block from rules_compendium."""
        route = owner_routes.get_monster(name)
        return await self._json("rules_compendium", route.method, route.path)

    async def narrate(self, request: dict[str, Any]) -> dict[str, Any]:
        """Ask The Watcher for DM narration. The response is returned as The Watcher sent it."""
        route = owner_routes.narrate()
        return await self._json("the_watcher", route.method, route.path, request)

    async def propose_action(self, request: dict[str, Any]) -> dict[str, Any]:
        """Propose an agent action to The Watcher. The DM can veto it before it takes effect."""
        route = owner_routes.propose_action()
        return await self._json("the_watcher", route.method, route.path, request)

    async def balance_encounter(
        self, party_levels: list[int], target_difficulty: str
    ) -> dict[str, Any]:
        """Ask rules_compendium to balance an encounter for a party."""
        route = owner_routes.balance_encounter()
        return await self._json(
            "rules_compendium",
            route.method,
            route.path,
            {"party_levels": party_levels, "target_difficulty": target_difficulty},
        )
