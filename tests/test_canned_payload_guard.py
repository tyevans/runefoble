"""Behaviour guard against canned gateway payloads (TASK-0597).

The gateway must not invent data when an owner is down (ADR-0015 b: the gateway returns no
substitute value). This test takes every HTTP route that the gateway publishes in its OpenAPI
document. It signs in as a real principal and points every owner at a closed port. No route may
then answer 200. A canned payload or an in-memory fallback would answer 200 here and fail the test.

Health probes are the only routes that answer without an owner. They report the gateway's own
liveness and the state of its probes, not data from an owner. Add a route to the allow list only
with a reason that says why the gateway answers it without an owner.
"""

from __future__ import annotations

import re

from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from runefoble_platform.service_client import OWNER_URL_FIELDS

from tests.helpers.live_services import closed_port_url

# Route paths (OpenAPI form) and methods that answer without an owner. Each entry needs a reason.
OWNER_FREE_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        # Liveness. The top-level status stays healthy while the process runs (TASK-0674). Owner
        # probe results appear in `downstream_services`, so the reply is status, not owner data.
        ("/healthz", "get"),
        # Kubernetes readiness. It states that this gateway process is ready.
        ("/readyz", "get"),
        # Sync health. It reports the state of the gateway's SpiceDB sync service.
        ("/api/v1/auth/sync/health", "get"),
    }
)

HTTP_METHODS = ("get", "post", "put", "patch", "delete")
PROBE_VALUE = "probe-id"


def _owner_env(service: str) -> str:
    """The environment variable of an owner base URL. The Watcher keeps its short name."""
    if service == "the_watcher":
        return "RUNEFOBLE_WATCHER_URL"
    return "RUNEFOBLE_" + OWNER_URL_FIELDS[service].upper()


def _published_routes() -> list[tuple[str, str]]:
    """Return every (method, concrete path) pair that the gateway publishes over HTTP."""
    routes = []
    for path, operations in gateway_app.openapi()["paths"].items():
        concrete = re.sub(r"\{[^}]+\}", PROBE_VALUE, path)
        for method in operations:
            if method in HTTP_METHODS and (path, method) not in OWNER_FREE_ROUTES:
                routes.append((method.upper(), concrete))
    return sorted(routes)


def test_no_gateway_route_answers_200_when_every_owner_is_down(monkeypatch, trusted_ws_issuer):
    routes = _published_routes()
    assert routes, "the gateway publishes no HTTP routes"

    for service in OWNER_URL_FIELDS:
        monkeypatch.setenv(_owner_env(service), closed_port_url())

    headers = {"Authorization": f"Bearer {trusted_ws_issuer.mint('user_canned_guard')}"}
    answered_200 = []
    with TestClient(gateway_app) as client:
        for method, path in routes:
            res = client.request(method, path, headers=headers)
            if res.status_code == 200:
                answered_200.append(f"{method} {path}")

    assert answered_200 == [], "routes answered 200 with owners down: " + ", ".join(answered_200)
