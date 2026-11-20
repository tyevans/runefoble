"""Blackbox Helm test: every app pod has readiness and startup probes (TASK-0929 to TASK-0933).

The rendered chart is the public output of the deployment. Kubernetes sends traffic to a pod
only when its readiness probe passes. A pod without a probe is Ready when its container
starts, so the first requests after a rollout can fail. Every service that has the dependency
gate (`/readyz`) must be probed there. A startup probe holds the liveness probe back until the
service listens. A cold start under a full restart can take more than 35 s (TASK-0933).

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
    "voice-agent": 8005,
    "campaign-lore": 8006,
    "rules-compendium": 8007,
    "asset-forge": 8008,
    "soundscape": 8009,
    "audience-studio": 8010,
    "campaign-analytics": 8011,
    "inference-worker": 8100,
    "gateway-mcp": 8012,
}
# The start budget of one cold start: failureThreshold x periodSeconds, in seconds.
MIN_STARTUP_BUDGET_S = 120


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


@pytest.mark.parametrize("deployment", APP_DEPLOYMENTS)
def test_every_app_pod_has_a_startup_probe_with_a_cold_start_budget(deployment: str) -> None:
    container = _containers()[deployment]
    startup = container["startupProbe"]
    assert startup["httpGet"]["port"] == container["ports"][0]["containerPort"]
    assert startup["httpGet"]["path"] == "/healthz"
    assert startup["periodSeconds"] * startup["failureThreshold"] >= MIN_STARTUP_BUDGET_S


@pytest.mark.parametrize("deployment", APP_DEPLOYMENTS)
def test_startup_probe_runs_before_the_readiness_and_liveness_probes(deployment: str) -> None:
    """Kubernetes holds the other probes until the startup probe passes. Do not delay them."""
    container = _containers()[deployment]
    assert container["readinessProbe"]["initialDelaySeconds"] <= 5
    if "livenessProbe" in container:
        assert container["livenessProbe"]["initialDelaySeconds"] <= 5
