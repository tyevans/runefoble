"""Blackbox Helm test: every app pod has a readiness probe (TASK-0929, TASK-0930, TASK-0931).

The rendered chart is the public output of the deployment. Kubernetes sends traffic to a pod
only when its readiness probe passes. A pod without a probe is Ready when its container
starts, so the first requests after a rollout can fail. The services that serve the
dependency gate (`/readyz`) must be probed there.

Governed by ADR-0005 and ADR-0015.
"""

from __future__ import annotations

import pytest

from tests.helpers.helm import render_chart

# Each Deployment that the chart renders from an entry of `.Values.services`.
APP_DEPLOYMENTS = (
    "gateway-api",
    "the-watcher",
    "board-state",
    "character-sheet",
    "game-session",
    "voice-agent",
    "campaign-lore",
    "rules-compendium",
    "asset-forge",
    "soundscape",
    "audience-studio",
    "campaign-analytics",
    "inference-worker",
    "gateway-mcp",
)
GATED = {
    "gateway-api": 8000,
    "the-watcher": 8001,
    "board-state": 8002,
    "character-sheet": 8003,
    "game-session": 8004,
    "campaign-lore": 8006,
    "asset-forge": 8008,
    "soundscape": 8009,
    "audience-studio": 8010,
}


def _containers() -> dict[str, dict]:
    return {
        doc["metadata"]["name"]: doc["spec"]["template"]["spec"]["containers"][0]
        for doc in render_chart()
        if doc.get("kind") == "Deployment"
    }


@pytest.mark.parametrize("deployment", APP_DEPLOYMENTS)
def test_every_app_pod_has_an_http_readiness_probe(deployment: str) -> None:
    container = _containers()[deployment]
    readiness = container["readinessProbe"]
    assert readiness["httpGet"]["port"] == container["ports"][0]["containerPort"]
    # Longer than the 2.5 s limit of one dependency check behind /readyz.
    assert readiness["timeoutSeconds"] == 3


@pytest.mark.parametrize(("deployment", "port"), sorted(GATED.items()))
def test_gated_services_are_ready_only_through_readyz(deployment: str, port: int) -> None:
    container = _containers()[deployment]
    assert container["readinessProbe"]["httpGet"] == {"path": "/readyz", "port": port}


def test_game_session_liveness_stays_on_healthz() -> None:
    container = _containers()["game-session"]
    assert container["livenessProbe"]["httpGet"] == {"path": "/healthz", "port": 8004}
