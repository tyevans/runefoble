import pytest
from gateway_api.main import app as gateway_app
from httpx import ASGITransport, AsyncClient

from tests.realtime_session import bearer


@pytest.mark.asyncio
async def test_gateway_health_and_docs():
    transport = ASGITransport(app=gateway_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Check health
        health_res = await client.get("/healthz")
        assert health_res.status_code == 200
        assert health_res.json()["status"] == "healthy"

        # Check OpenAPI JSON documentation endpoint
        docs_res = await client.get("/openapi.json")
        assert docs_res.status_code == 200
        openapi = docs_res.json()
        assert openapi["info"]["title"] == "Runefoble Platform Unified Gateway"
        assert "/api/v1/sessions/{session_id}" in openapi["paths"]
        assert "/api/v1/boards/{session_id}" in openapi["paths"]


def test_gateway_speak_and_act(gateway, table_for):
    _, session_id = table_for("dm_dora", {"valeros-player": "player"})
    res = gateway.post(
        "/api/v1/watcher/speak-and-act",
        params={
            "transcript": "Valeros advances 2 squares",
            "speaker_name": "Valeros",
            "session_id": session_id,
        },
        headers=bearer("valeros-player"),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["speaker"] == "Valeros"
    assert "Valeros stepped forward" in data["action_taken"]
