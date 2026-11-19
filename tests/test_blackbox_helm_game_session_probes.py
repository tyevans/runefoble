"""Blackbox Helm test: the game_session pod is Ready only through `/readyz` (TASK-0929).

The rendered chart is the public output of the deployment. Kubernetes sends traffic to a pod
only when its readiness probe passes, so the probe must call the route that waits for the
event store, SpiceDB and Redis.

Governed by ADR-0005 and ADR-0015.
"""

from __future__ import annotations

from tests.helpers.helm import render_chart


def _container(deployment: str) -> dict:
    deployments = {
        doc["metadata"]["name"]: doc for doc in render_chart() if doc.get("kind") == "Deployment"
    }
    return deployments[deployment]["spec"]["template"]["spec"]["containers"][0]


def test_game_session_readiness_probe_waits_for_dependencies() -> None:
    container = _container("game-session")
    readiness = container["readinessProbe"]
    assert readiness["httpGet"] == {"path": "/readyz", "port": 8004}
    assert readiness["timeoutSeconds"] == 3
    assert container["livenessProbe"]["httpGet"] == {"path": "/healthz", "port": 8004}


def test_other_readiness_probes_keep_the_default_time_limit() -> None:
    readiness = _container("voice-agent")["readinessProbe"]
    assert readiness["httpGet"]["path"] == "/healthz"
    assert readiness["timeoutSeconds"] == 1
