"""Blackbox checks for the public ingress WebSocket route and the Vite dev proxy.

The tests use only the rendered Helm manifests and the frontend Vite config.
They do not reach into service internals.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

HELM_CHART = Path("deployments/helm/runefoble")
VITE_CONFIG = Path("frontend/vite.config.ts")


def _render_ingress_documents() -> list[dict]:
    """Render the umbrella chart and return every Ingress manifest."""
    if not shutil.which("helm"):
        pytest.skip("helm CLI not available")

    proc = subprocess.run(
        ["helm", "template", "runefoble", str(HELM_CHART)],
        capture_output=True,
        text=True,
        check=True,
    )
    docs = [doc for doc in yaml.safe_load_all(proc.stdout) if doc]
    return [doc for doc in docs if doc.get("kind") == "Ingress"]


def test_ingress_routes_websocket_path_to_gateway_on_every_host():
    """Every ingress host sends /ws/... to gateway-api:8000 with Prefix matching."""
    ingresses = _render_ingress_documents()
    assert len(ingresses) == 1, "expected exactly one Ingress manifest"

    rules = ingresses[0]["spec"]["rules"]
    assert rules, "ingress has no host rules"

    for rule in rules:
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
    ingresses = _render_ingress_documents()
    for rule in ingresses[0]["spec"]["rules"]:
        paths = [p["path"] for p in rule["http"]["paths"]]
        assert "/ws" in paths, f"host {rule['host']} has no /ws path"
        assert paths.index("/ws") < paths.index("/"), (
            f"host {rule['host']} lists /ws after the frontend catch-all"
        )


def test_ingress_keeps_api_route_to_gateway():
    """Adding /ws must not change the existing /api route."""
    ingresses = _render_ingress_documents()
    for rule in ingresses[0]["spec"]["rules"]:
        api_routes = [p for p in rule["http"]["paths"] if p["path"] == "/api"]
        assert api_routes, f"host {rule['host']} lost its /api route"
        assert api_routes[0]["backend"]["service"]["name"] == "gateway-api"


def test_vite_dev_proxy_forwards_ws_with_upgrade_support():
    """The Vite dev proxy forwards /ws to the gateway with ws: true."""
    source = VITE_CONFIG.read_text(encoding="utf-8")
    match = re.search(r"'/ws':\s*\{(?P<body>[^}]*)\}", source, re.DOTALL)
    assert match, "Vite proxy has no '/ws' entry"
    body = match.group("body")
    assert "ws: true" in body, "Vite '/ws' proxy entry does not enable ws: true"
    assert "gatewayWsUrl" in body, "Vite '/ws' proxy entry does not target the gateway"
