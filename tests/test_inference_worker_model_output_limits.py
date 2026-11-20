"""Blackbox tests: model output that the token limit cut off, or that has wrong field types.

The worker runs as an ASGI app. The model runtime is a fake OpenAI-compatible server, which is a
true process boundary. Each failure is an explicit 503 with a logged reason (ADR-0015).
"""

from __future__ import annotations

import logging
import os
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from inference_worker import api
from inference_worker.llm_factory import build_llm_port
from runefoble_platform.service_credential import SERVICE_CREDENTIAL_HEADER

from tests.helpers.inference_worker_port import install_worker_port

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
UNAVAILABLE = {"error": "backend_unavailable", "backend": "openai_compatible"}


async def _post(path: str, payload: dict[str, Any]):
    async with AsyncClient(
        transport=ASGITransport(app=api.app, raise_app_exceptions=False),
        base_url="http://test",
        headers=WORKER_AUTH,
    ) as ac:
        return await ac.post(path, json=payload)


@pytest.mark.asyncio
async def test_cut_off_narration_is_503_with_a_logged_reason(monkeypatch, fake_llm, caplog):
    """A reply that stops at the token limit is not used, even when its text parses."""
    fake_llm.content = '{"narration": "The door groans."}'
    fake_llm.finish_reason = "length"
    install_worker_port(monkeypatch, build_llm_port(fake_llm.settings()))

    with caplog.at_level(logging.WARNING):
        resp = await _post("/inference/v1/dm-narration", NARRATION_PAYLOAD)

    assert resp.status_code == 503
    assert resp.json() == UNAVAILABLE
    assert "token limit" in caplog.text


@pytest.mark.asyncio
async def test_narration_prompt_asks_for_a_short_answer(monkeypatch, fake_llm):
    """The answer must fit the token limit, so the prompt sets a word limit."""
    fake_llm.content = '{"narration": "The door groans."}'
    install_worker_port(monkeypatch, build_llm_port(fake_llm.settings()))

    resp = await _post("/inference/v1/dm-narration", NARRATION_PAYLOAD)

    assert resp.status_code == 200
    system_prompt = str(fake_llm.requests[-1]["messages"][0]["content"])
    assert "at most 60 words" in system_prompt


@pytest.mark.asyncio
async def test_intent_field_of_the_wrong_type_is_503_not_500(monkeypatch, fake_llm, caplog):
    """A model that writes `false` where the contract has a dice expression gets an explicit 503."""
    fake_llm.content = '{"action_type": "attack", "dice_check_required": false}'
    install_worker_port(monkeypatch, build_llm_port(fake_llm.settings()))

    with caplog.at_level(logging.WARNING):
        resp = await _post("/inference/v1/intent", INTENT_PAYLOAD)

    assert resp.status_code == 503
    assert resp.json() == UNAVAILABLE
    assert "dice_check_required" in caplog.text
