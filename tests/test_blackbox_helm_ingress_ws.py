"""Blackbox checks for the public ingress WebSocket route and the Vite dev proxy.

The tests use only the rendered Helm manifests and the frontend Vite config.
They do not reach into service internals.
"""

from tests.helpers.helm import render_chart

# Zitadel has its own host. It is not an application host and has no /ws route.
ZITADEL_HOST = "auth.localhost"


def _render_ingress_documents() -> list[dict]:
    """Render the umbrella chart and return every Ingress manifest."""
    return [doc for doc in render_chart() if doc.get("kind") == "Ingress"]


def _app_rules() -> list[dict]:
    """Return the ingress host rules that serve the application, excluding the Zitadel host."""
    ingresses = _render_ingress_documents()
    assert len(ingresses) == 1, "expected exactly one Ingress manifest"
    rules = [r for r in ingresses[0]["spec"]["rules"] if r["host"] != ZITADEL_HOST]
    assert rules, "ingress has no application host rules"
    return rules


def test_ingress_routes_websocket_path_to_gateway_on_every_host():
    """Every application ingress host sends /ws/... to gateway-api:8000 with Prefix matching."""
    for rule in _app_rules():
        paths = rule["http"]["paths"]
        ws_paths = [p for p in paths if p["path"] == "/ws"]
        assert ws_paths, f"host {rule['host']} has no /ws path"

        ws_route = ws_paths[0]
        assert ws_route["pathType"] == "Prefix", f"host {rule['host']} /ws is not Prefix"
        assert ws_route["backend"]["service"]["name"] == "gateway-api", (
            f"host {rule['host']} /ws does not target gateway-api"
        )
        assert ws_route["backend"]["service"]["port"]["number"] == 8000, (
            f"host {rule['host']} /ws does not target port 8000"
        )


def test_ingress_ws_route_precedes_frontend_catch_all():
    """The /ws rule sits before the frontend catch-all so it is not shadowed."""
    for rule in _app_rules():
        paths = [p["path"] for p in rule["http"]["paths"]]
        assert "/ws" in paths, f"host {rule['host']} has no /ws path"
        assert paths.index("/ws") < paths.index("/"), (
            f"host {rule['host']} lists /ws after the frontend catch-all"
        )


def test_ingress_keeps_api_route_to_gateway():
    """Adding /ws must not change the existing /api route."""
    for rule in _app_rules():
        api_routes = [p for p in rule["http"]["paths"] if p["path"] == "/api"]
        assert api_routes, f"host {rule['host']} lost its /api route"
        assert api_routes[0]["backend"]["service"]["name"] == "gateway-api"


def test_ingress_routes_board_socket_path_to_board_state_on_every_host():
    """Every application host sends /ws/boards/... to board-state:8002, which owns the board socket.

    gateway-api has no /ws/boards route. Traefik gives the longer prefix the higher priority, and
    the rule is listed before /ws, so the board socket never reaches the gateway (TASK-0928).
    """
    for rule in _app_rules():
        paths = rule["http"]["paths"]
        board_routes = [p for p in paths if p["path"] == "/ws/boards"]
        assert board_routes, f"host {rule['host']} has no /ws/boards path"
        route = board_routes[0]
        assert route["pathType"] == "Prefix"
        assert route["backend"]["service"]["name"] == "board-state"
        assert route["backend"]["service"]["port"]["number"] == 8002
        listed = [p["path"] for p in paths]
        assert listed.index("/ws/boards") < listed.index("/ws"), (
            f"host {rule['host']} lists /ws/boards after /ws"
        )
