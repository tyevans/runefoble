"""Smoke test: the gateway test package collects and runs (TASK-0597)."""

from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app


def test_gateway_health_endpoint_answers_through_the_public_app():
    with TestClient(gateway_app) as client:
        res = client.get("/healthz")

    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
