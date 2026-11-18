"""Blackbox tests for the inference worker LLM port selected at start-up.

The worker runs through its public HTTP routes and its app lifespan. A stub port stands in
for an engine that fails. Unreachable engines are real closed localhost ports.
"""

import os
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from inference_worker import api
from inference_worker.config import WorkerSettings
from inference_worker.ports import Completion, LLMPort
from pydantic import ValidationError
from runefoble_platform.engine_ports import EngineUnavailableError
from runefoble_platform.service_credential import SERVICE_CREDENTIAL_HEADER

from tests.helpers.inference_worker_port import install_worker_port
from tests.helpers.live_services import closed_port_url

WORKER_AUTH = {SERVICE_CREDENTIAL_HEADER: os.environ["RUNEFOBLE_SERVICE_CREDENTIAL"]}

INTENT_PAYLOAD: dict[str, Any] = {
    "campaign_id": "camp-1",
    "session_id": "sess-1",
    "speaker_id": "spk-1",
    "speaker_name": "Merisiel",
    "transcript": "I attack the skeleton with my rapier",
    "visible_tokens": [],
}
NARRATION_PAYLOAD: dict[str, Any] = {
    "campaign_id": "camp-1",
    "session_id": "sess-1",
    "scene_environment": "Forgotten Library",
    "guidance_prompt": "What do the adventurers see?",
}
STAND_IN_PAYLOAD: dict[str, Any] = {
    "campaign_id": "camp-1",
    "session_id": "sess-1",
    "character_name": "Seoni",
    "character_class": "Sorcerer",
    "penalties": ["drunk"],
    "visible_enemies": ["Orc Chieftain"],
}
ENDPOINTS = [
    ("/inference/v1/intent", INTENT_PAYLOAD),
    ("/inference/v1/dm-narration", NARRATION_PAYLOAD),
    ("/inference/v1/stand-in-action", STAND_IN_PAYLOAD),
]


class _DownPort(LLMPort):
    """A stub engine that starts and then fails every completion."""

    engine_name = "stub_engine"

    async def check_ready(self) -> None:
        return None

    async def complete(self, system_prompt: str, user_prompt: str) -> Completion:
        raise EngineUnavailableError(
            "backend_unavailable", self.engine_name, "stub engine is down", engine_field="backend"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(("path", "payload"), ENDPOINTS)
async def test_failing_port_returns_503_with_backend_body(monkeypatch, path, payload):
    install_worker_port(monkeypatch, _DownPort())

    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        resp = await ac.post(path, json=payload)

    assert resp.status_code == 503
    assert resp.json() == {"error": "backend_unavailable", "backend": "stub_engine"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "settings",
    [
        WorkerSettings(backend="openai_compatible", openai_base_url=f"{closed_port_url()}/v1"),
        WorkerSettings(backend="ollama", ollama_base_url=closed_port_url()),
    ],
    ids=["openai_compatible", "ollama"],
)
async def test_unreachable_engine_stops_start_up(monkeypatch, settings):
    monkeypatch.setattr(api, "settings", settings)

    with pytest.raises(EngineUnavailableError) as info:
        async with api.lifespan(api.app):
            pass

    assert info.value.error_code == "backend_unavailable"
    assert info.value.engine == settings.backend


@pytest.mark.asyncio
async def test_explicit_mock_backend_starts_and_serves_every_route(monkeypatch):
    monkeypatch.setattr(api, "settings", WorkerSettings(backend="mock"))
    for name in ("llm_port", "intent_graph", "narration_graph", "stand_in_graph"):
        monkeypatch.setattr(api, name, getattr(api, name))

    async with (
        api.lifespan(api.app),
        AsyncClient(
            transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
        ) as ac,
    ):
        intent = await ac.post("/inference/v1/intent", json=INTENT_PAYLOAD)
        narration = await ac.post("/inference/v1/dm-narration", json=NARRATION_PAYLOAD)
        stand_in = await ac.post("/inference/v1/stand-in-action", json=STAND_IN_PAYLOAD)
        health = await ac.get("/healthz")

    for resp in (intent, narration, stand_in):
        assert resp.status_code == 200
        assert resp.json()["source"] == "mock"
    assert health.json()["backend"] == "mock"


def test_unknown_backend_value_fails_start_up_and_names_allowed_values():
    with pytest.raises(ValidationError) as info:
        WorkerSettings(backend="auto")

    message = str(info.value)
    for allowed in ("openai_compatible", "ollama", "mock"):
        assert allowed in message
