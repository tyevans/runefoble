"""Owner and mode of every public route that the gateway mounts (TASK-0598).

The reference page docs/reference/gateway-route-ownership.md is generated from `owned_routes`.
The page never holds a row that the app does not mount, and a mounted route never lacks a row.

An owner is found in this order:

1. A `ProxyRoute` row in a router's `ROUTES` tuple. The row names the owner service.
2. A `service=` argument in the handler body. The handler calls `forward_json`, `forward_bytes`
   or `relay_websocket` with that service. The value is a literal or a module constant.
3. `DECLARED`. A route that reads several owners, or none, names its owners here.

A route that matches none of these raises `ValueError`. The gateway never guesses an owner.
"""

from __future__ import annotations

import ast
import inspect
import pkgutil
import textwrap
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from importlib import import_module
from types import ModuleType
from typing import Any, Literal

import gateway_api.routers as routers_package
from fastapi import FastAPI
from fastapi.routing import APIRoute
from gateway_api.proxy_table import ProxyRoute
from starlette.routing import WebSocketRoute

Mode = Literal["proxy", "relay", "local"]
GATEWAY = "gateway_api"
WEBSOCKET = "WS"
_FORWARDERS = frozenset({"forward_json", "forward_bytes", "relay_websocket"})
_CHARACTER_OWNERS = "character_sheet, game_session"
_SESSION_OWNERS = "board_state, voice_agent, the_watcher"
_SPECTATE_OWNERS = "game_session, board_state"

# Routes whose owners the handler body does not name in one `service=` argument.
# Each entry names the owners that the module docstring gives for the route.
DECLARED: dict[tuple[str, str], tuple[str, Mode]] = {
    ("GET", "/healthz"): (GATEWAY, "local"),
    ("GET", "/readyz"): (GATEWAY, "local"),
    ("GET", "/api/v1/auth/sync/health"): (GATEWAY, "local"),
    (WEBSOCKET, "/ws/campaigns/{campaign_id}"): (GATEWAY, "local"),
    (WEBSOCKET, "/ws/session/{session_id}"): (_SESSION_OWNERS, "relay"),
    ("GET", "/api/v1/spectate/{session_id}"): (_SPECTATE_OWNERS, "proxy"),
    (WEBSOCKET, "/ws/spectator/{session_id}"): (_SPECTATE_OWNERS, "relay"),
    ("GET", "/overlay/party-vitals/{session_id}"): (_SPECTATE_OWNERS, "proxy"),
    (WEBSOCKET, "/ws/overlay/{session_id}"): (_SPECTATE_OWNERS, "relay"),
    ("GET", "/api/v1/characters"): (_CHARACTER_OWNERS, "proxy"),
    ("POST", "/api/v1/characters"): (_CHARACTER_OWNERS, "proxy"),
    ("GET", "/api/v1/characters/{character_id}"): (_CHARACTER_OWNERS, "proxy"),
    ("PATCH", "/api/v1/characters/{character_id}/campaign"): (_CHARACTER_OWNERS, "proxy"),
    ("POST", "/api/v1/characters/{character_id}/health"): (_CHARACTER_OWNERS, "proxy"),
    ("POST", "/api/v1/characters/{character_id}/equipment"): (_CHARACTER_OWNERS, "proxy"),
    ("DELETE", "/api/v1/characters/{character_id}/equipment/{slot}"): (
        _CHARACTER_OWNERS,
        "proxy",
    ),
    ("POST", "/api/v1/characters/{character_id}/inventory"): (_CHARACTER_OWNERS, "proxy"),
    ("DELETE", "/api/v1/characters/{character_id}/inventory/{item_id}"): (
        _CHARACTER_OWNERS,
        "proxy",
    ),
    ("POST", "/api/v1/characters/{character_id}/conditions"): (_CHARACTER_OWNERS, "proxy"),
    ("DELETE", "/api/v1/characters/{character_id}/conditions/{condition}"): (
        _CHARACTER_OWNERS,
        "proxy",
    ),
    ("POST", "/api/v1/characters/{character_id}/spells/cast"): (_CHARACTER_OWNERS, "proxy"),
    ("POST", "/api/v1/characters/{character_id}/spells/prepare"): (_CHARACTER_OWNERS, "proxy"),
    ("PUT", "/api/v1/characters/{character_id}/guardrails"): (_CHARACTER_OWNERS, "proxy"),
}


@dataclass(frozen=True)
class OwnedRoute:
    """One public route the gateway mounts, with its owner."""

    method: str
    path: str
    owner: str
    mode: Mode
    source: str


def owned_routes(app: FastAPI) -> list[OwnedRoute]:
    """Return one row per mounted public route, sorted by path and method.

    Documentation routes (`/docs`, `/openapi.json`, `/redoc`) are not API routes. They are
    Starlette `Route` objects, and this function skips them.
    """
    rows_by_key = _proxy_rows()
    rows = []
    for path, route in _mounted_routes(app):
        for method in _methods(route):
            key = (method, path)
            owner, mode, source = _owner_of(key, route, rows_by_key)
            rows.append(OwnedRoute(method, path, owner, mode, source))
    return sorted(rows, key=lambda row: (row.path, row.method))


def _mounted_routes(app: FastAPI) -> Iterator[tuple[str, APIRoute | WebSocketRoute]]:
    """Yield (full path, route) for every API route and WebSocket route on the app."""
    for top in app.routes:
        if hasattr(top, "effective_route_contexts"):
            # FastAPI includes a router as a wrapper. Its effective contexts carry full paths.
            for context in top.effective_route_contexts():
                if isinstance(context.original_route, (APIRoute, WebSocketRoute)):
                    # A WebSocket context carries no path of its own. Its Starlette route does.
                    path = context.path or _starlette_path(context.starlette_route)
                    yield path, context.original_route
        elif isinstance(top, (APIRoute, WebSocketRoute)):
            yield top.path, top


def _starlette_path(starlette_route: object) -> str:
    path = getattr(starlette_route, "path", None)
    if not isinstance(path, str) or not path:
        raise ValueError(f"mounted route has no path: {starlette_route!r}")
    return path


def _methods(route: APIRoute | WebSocketRoute) -> list[str]:
    if isinstance(route, WebSocketRoute):
        return [WEBSOCKET]
    return sorted(route.methods)


def _proxy_rows() -> dict[tuple[str, str], tuple[str, str]]:
    """Map (method, public path) to (owner service, defining module) for each ProxyRoute row."""
    rows: dict[tuple[str, str], tuple[str, str]] = {}
    for module in _router_modules():
        for row in getattr(module, "ROUTES", ()):
            if isinstance(row, ProxyRoute):
                rows[(row.method, row.public_path)] = (row.service, module.__name__)
    return rows


def _router_modules() -> Iterator[ModuleType]:
    prefix = routers_package.__name__ + "."
    for info in pkgutil.walk_packages(routers_package.__path__, prefix):
        yield import_module(info.name)


def _owner_of(
    key: tuple[str, str],
    route: APIRoute | WebSocketRoute,
    rows: dict[tuple[str, str], tuple[str, str]],
) -> tuple[str, Mode, str]:
    mode: Mode = "relay" if key[0] == WEBSOCKET else "proxy"
    if key in rows:
        owner, source = rows[key]
        return owner, mode, source
    source = route.endpoint.__module__
    if key in DECLARED:
        owner, declared_mode = DECLARED[key]
        return owner, declared_mode, source
    services = _forwarded_services(route.endpoint)
    if len(services) != 1:
        raise ValueError(f"no single owner for {key[0]} {key[1]}: found {sorted(services)}")
    return services.pop(), mode, source


def _forwarded_services(endpoint: Callable[..., Any]) -> set[str]:
    """Return the `service=` values that the handler passes to a forwarding helper."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(endpoint)))
    module_globals = vars(inspect.getmodule(endpoint))
    services: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_name(node.func) not in _FORWARDERS:
            continue
        for keyword in node.keywords:
            if keyword.arg == "service":
                services.add(_resolve_service(keyword.value, module_globals))
    return services


def _call_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _resolve_service(value: ast.expr, module_globals: dict[str, Any]) -> str:
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    if isinstance(value, ast.Name) and isinstance(module_globals.get(value.id), str):
        return module_globals[value.id]
    raise ValueError(f"cannot resolve the owner service from {ast.dump(value)}")
