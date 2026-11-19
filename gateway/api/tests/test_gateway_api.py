from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app


def test_gateway_health_and_docs():
    # The lifespan builds the upstream registry that /healthz probes, so the client enters it.
    with TestClient(gateway_app) as client:
        # Check health
        health_res = client.get("/healthz")
        assert health_res.status_code == 200
        assert health_res.json()["status"] == "healthy"

        # Check OpenAPI JSON documentation endpoint
        docs_res = client.get("/openapi.json")
        assert docs_res.status_code == 200
        openapi = docs_res.json()
        assert openapi["info"]["title"] == "Runefoble Platform Unified Gateway"
        assert "/api/v1/sessions/{session_id}" in openapi["paths"]
        assert "/api/v1/boards/{session_id}" in openapi["paths"]
