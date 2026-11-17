"""Blackbox tests for the inference worker Redis Streams consumer message contract.

The Redis server is a true process boundary. The fake client below records the XADD and XACK
calls that the consumer makes on the stream. It replaces only the transport, not the code under
test. The mock LLM backend is selected by explicit configuration.
"""

import asyncio
import json
from typing import Any

import pytest
from inference_worker import redis_consumer
from inference_worker.config import WorkerSettings
from inference_worker.llm_client import MultiBackendLLMClient
from inference_worker.redis_consumer import RedisInferenceConsumer
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import ResponseError

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
async def test_unknown_task_type_publishes_error_result_and_acknowledges(consumer):
    worker, fake = consumer

    await worker._process_message("2-0", {"type": "no_such_task", "payload": "{}"})

    assert len(fake.added) == 1
    _stream, published = fake.added[0]
    assert published["status"] == "error"
    assert published["task_type"] == "no_such_task"
    assert "no_such_task" in published["error"]
    assert published["correlation_id"] == "2-0"
    assert fake.acked == ["2-0"]


@pytest.mark.asyncio
async def test_message_without_type_publishes_error_result_and_acknowledges(consumer):
    worker, fake = consumer

    await worker._process_message(
        "3-0", {"payload": json.dumps(NARRATION_PAYLOAD), "correlation_id": "corr-3"}
    )

    assert len(fake.added) == 1
    _stream, published = fake.added[0]
    assert published["status"] == "error"
    assert published["correlation_id"] == "corr-3"
    assert fake.acked == ["3-0"]


@pytest.mark.asyncio
async def test_message_without_payload_publishes_error_result_and_acknowledges(consumer):
    worker, fake = consumer

    await worker._process_message("4-0", {"type": "generate_narration", "correlation_id": "corr-4"})

    assert len(fake.added) == 1
    _stream, published = fake.added[0]
    assert published["status"] == "error"
    assert published["task_type"] == "generate_narration"
    assert published["correlation_id"] == "corr-4"
    assert fake.acked == ["4-0"]


class FakeStartupRedis:
    """Stands in for the Redis server at the transport boundary only."""

    def __init__(self, group_create_error: Exception | None) -> None:
        self._group_create_error = group_create_error
        self.closed = False

    async def xgroup_create(self, **_kwargs: Any) -> None:
        if self._group_create_error is not None:
            raise self._group_create_error

    async def xreadgroup(self, **_kwargs: Any) -> list:
        await asyncio.sleep(0)
        return []

    async def close(self) -> None:
        self.closed = True


def _install_fake_redis(monkeypatch: pytest.MonkeyPatch, fake: FakeStartupRedis) -> None:
    monkeypatch.setattr(redis_consumer.aioredis, "from_url", lambda *_a, **_k: fake)


def _enabled_worker() -> RedisInferenceConsumer:
    settings = WorkerSettings(backend="mock", redis_enabled=True)
    return RedisInferenceConsumer(settings, MultiBackendLLMClient(settings))


@pytest.mark.asyncio
async def test_start_succeeds_when_consumer_group_already_exists(monkeypatch):
    fake = FakeStartupRedis(ResponseError("BUSYGROUP Consumer Group name already exists"))
    _install_fake_redis(monkeypatch, fake)
    worker = _enabled_worker()

    await worker.start()
    await worker.stop()

    assert fake.closed is True


@pytest.mark.asyncio
async def test_start_raises_on_wrongtype_group_create_error(monkeypatch):
    fake = FakeStartupRedis(
        ResponseError("WRONGTYPE Operation against a key holding the wrong kind of value")
    )
    _install_fake_redis(monkeypatch, fake)
    worker = _enabled_worker()

    with pytest.raises(ResponseError, match="WRONGTYPE"):
        await worker.start()


@pytest.mark.asyncio
async def test_start_raises_when_redis_is_unreachable(monkeypatch):
    fake = FakeStartupRedis(RedisConnectionError("Error 111 connecting to 127.0.0.1:6379"))
    _install_fake_redis(monkeypatch, fake)
    worker = _enabled_worker()

    with pytest.raises(RedisConnectionError):
        await worker.start()
