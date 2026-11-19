"""Blackbox deployability tests for the inference worker Helm deployment (TASK-0622).

Governed by ADR-0005 (Kind and Helm) and Hard Invariant 5 (Swagger hub registration).
The tests render the umbrella chart with `helm template` and read the output documents.
They use no private state and no backdoors.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from tests.helpers.helm import render_chart

REPO_ROOT = Path(__file__).resolve().parent.parent
CHART = REPO_ROOT / "deployments" / "helm" / "runefoble"
VALUES = CHART / "values.yaml"
WORKER_PORT = 8100
WORKER_URL = f"http://inference-worker:{WORKER_PORT}/openapi.json"


def _rendered_documents() -> list[dict]:
    return render_chart()


def _find(documents: list[dict], kind: str, name: str) -> dict:
    matches = [d for d in documents if d.get("kind") == kind and d["metadata"]["name"] == name]
    assert len(matches) == 1, f"expected one {kind} named {name}, found {len(matches)}"
    return matches[0]


def test_chart_renders_inference_worker_service_on_port_8100():
    """The chart renders a ClusterIP Service `inference-worker` that exposes port 8100."""
    service = _find(_rendered_documents(), "Service", "inference-worker")

    assert service["spec"]["type"] == "ClusterIP"
    assert service["spec"]["ports"] == [{"port": WORKER_PORT, "targetPort": WORKER_PORT}]
    assert service["spec"]["selector"] == {"app": "inference-worker"}


def test_chart_renders_inference_worker_deployment_with_probe_and_env():
    """The Deployment serves on 8100, probes /healthz, and keeps the Redis consumer off."""
    deployment = _find(_rendered_documents(), "Deployment", "inference-worker")
    container = deployment["spec"]["template"]["spec"]["containers"][0]

    assert container["image"] == "runefoble/inference-worker:0.1.0"
    assert container["ports"] == [{"containerPort": WORKER_PORT}]

    env = {item["name"]: item.get("value") for item in container["env"]}
    assert env["RUNEFOBLE_WORKER_HOST"] == "0.0.0.0"
    assert env["RUNEFOBLE_WORKER_PORT"] == str(WORKER_PORT)
    assert env["RUNEFOBLE_WORKER_BACKEND"] == "openai_compatible"
    assert "RUNEFOBLE_WORKER_OPENAI_BASE_URL" in env
    assert env["RUNEFOBLE_WORKER_REDIS_ENABLED"] == "false"
    credential = next(
        item for item in container["env"] if item["name"] == "RUNEFOBLE_SERVICE_CREDENTIAL"
    )
    assert credential["valueFrom"]["secretKeyRef"] == {
        "name": "runefoble-credentials",
        "key": "service-credential",
    }

    probe = container["readinessProbe"]["httpGet"]
    assert probe == {"path": "/healthz", "port": WORKER_PORT}


def test_swagger_hub_lists_inference_worker_openapi():
    """The Swagger UI aggregator lists the worker once, and no spec URL is listed twice."""
    documents = _rendered_documents()
    swagger = _find(documents, "Deployment", "swagger-ui")
    container = swagger["spec"]["template"]["spec"]["containers"][0]
    urls = next(item["value"] for item in container["env"] if item["name"] == "URLS")

    entries = yaml.safe_load(urls) if isinstance(urls, str) else urls
    urls_listed = [entry["url"] for entry in entries]
    assert urls_listed.count(WORKER_URL) == 1
    assert len(urls_listed) == len(set(urls_listed))


def test_values_declare_inference_worker_service():
    """values.yaml declares the worker image, port, backend, and an empty base URL."""
    values = yaml.safe_load(VALUES.read_text(encoding="utf-8"))
    worker = values["services"]["inferenceWorker"]

    assert worker["image"] == "runefoble/inference-worker:0.1.0"
    assert worker["port"] == WORKER_PORT
    assert worker["replicas"] == 1
    assert worker["backend"] == "openai_compatible"
    assert worker["openaiCompatibleBaseUrl"] == ""
