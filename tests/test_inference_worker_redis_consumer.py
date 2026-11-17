"""Blackbox tests for the inference worker Redis Streams consumer message contract.

The Redis server is a true process boundary. The fake client below records the XADD and XACK
calls that the consumer makes on the stream. It replaces only the transport, not the code under
test. The mock LLM backend is selected by explicit configuration.
"""

import json
from typing import Any

import pytest
from inference_worker.config import WorkerSettings
from inference_worker.llm_client import MultiBackendLLMClient
from inference_worker.redis_consumer import RedisInferenceConsumer

NARRATION_PAYLOAD: dict[str, Any] = {
    "campaign_id": "camp-1",
    "session_id": "sess-1",
    "scene_environment": "Forgotten Library",
    "guidance_prompt": "What do the adventurers see?",
}


class FakeRedisStream:
    """Records stream writes and acknowledgements. Stands in for the Redis server only."""

    def __init__(self) -> None:
        self.added: list[tuple[str, dict[str, str]]] = []
        self.acked: list[str] = []

    async def xadd(self, stream: str, fields: dict[str, str]) -> None:
        self.added.append((stream, fields))

    async def xack(self, stream: str, group: str, message_id: str) -> None:
        self.acked.append(message_id)


@pytest.fixture
def consumer() -> tuple[RedisInferenceConsumer, FakeRedisStream]:
    settings = WorkerSettings(backend="mock")
    worker = RedisInferenceConsumer(settings, MultiBackendLLMClient(settings))
    fake = FakeRedisStream()
    worker._redis = fake  # type: ignore[assignment]
    return worker, fake


@pytest.mark.asyncio
async def test_narration_message_publishes_result_and_acknowledges(consumer):
    worker, fake = consumer
    fields = {
        "type": "generate_narration",
        "payload": json.dumps(NARRATION_PAYLOAD),
        "correlation_id": "corr-1",
    }

    await worker._process_message("1-0", fields)

    assert len(fake.added) == 1
    _stream, published = fake.added[0]
    assert published["correlation_id"] == "corr-1"
    assert published["task_type"] == "generate_narration"
    assert json.loads(published["result"])["source"] == "mock"
    assert fake.acked == ["1-0"]


@pytest.mark.asyncio
async def test_unknown_task_type_is_not_published_or_acknowledged(consumer):
    worker, fake = consumer

    await worker._process_message("2-0", {"type": "no_such_task", "payload": "{}"})

    assert fake.added == []
    assert fake.acked == []


@pytest.mark.asyncio
async def test_message_without_type_is_not_published_or_acknowledged(consumer):
    worker, fake = consumer

    await worker._process_message("3-0", {"payload": json.dumps(NARRATION_PAYLOAD)})

    assert fake.added == []
    assert fake.acked == []


@pytest.mark.asyncio
async def test_message_without_payload_is_not_published_or_acknowledged(consumer):
    worker, fake = consumer

    await worker._process_message("4-0", {"type": "generate_narration"})

    assert fake.added == []
    assert fake.acked == []
