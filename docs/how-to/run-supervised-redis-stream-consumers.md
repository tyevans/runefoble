# How-To: Run Supervised Redis Stream Consumers

Use this recipe when a service must read a Redis Stream. The helpers live in `runefoble_platform.stream_consumer`. Each service starts its consumers in its FastAPI lifespan and reports them on `/healthz`.

## Rules

1. One start point. Build the consumer set and start it in the lifespan. Do not start a loop at import time.
2. Start-up fails loudly. `SupervisedStreamConsumers.start()` raises when a consumer group cannot be created. Do not catch that error.
3. Acknowledge after success. The handler runs first. The message is acknowledged only when the handler returns.
4. Dead-letter failures. A handler that raises routes the message to `{stream}.dlq`, then acknowledges it. The original message does not stay pending.
5. Report runtime failures. A failed read loop is logged at `ERROR`. Its `status` becomes `failed`. Publish the status on `/healthz`.

## Step 1: Build and Start the Consumer Set

Use the shared bus that the service already builds. Read the client from the bus. Do not read private attributes.

```python
import contextlib
from collections.abc import AsyncIterator

from fastapi import FastAPI
from runefoble_platform.consumer_group import RedisConsumerGroup
from runefoble_platform.redis_bus import RedisStreamsEventBus
from runefoble_platform.stream_consumer import StreamConsumer, SupervisedStreamConsumers


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    bus = RedisStreamsEventBus(redis_url=settings.redis_url)
    consumers = SupervisedStreamConsumers(
        "orders",
        [
            StreamConsumer(
                consumer_group=RedisConsumerGroup(client=await bus.get_client()),
                stream="runefoble.events.session",
                group_name="orders_workers",
                consumer_name="orders_consumer_1",
                handler=handle_session_event,
            )
        ],
    )
    await consumers.start()
    app.state.consumers = {"orders": consumers}
    try:
        yield
    finally:
        await consumers.stop()
        await bus.close()
```

## Step 2: Report Status on `/healthz`

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from runefoble_platform.stream_consumer import consumer_statuses


@app.get("/healthz")
def health_check(request: Request) -> JSONResponse:
    statuses = consumer_statuses(getattr(request.app.state, "consumers", {}))
    healthy = all(status == "running" for status in statuses.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ok" if healthy else "degraded",
            "service": "orders",
            "consumers": statuses,
        },
    )
```

A `503` tells the orchestrator that the pod lost a consumer. Liveness probes can restart the pod.

## Step 3: Test Through the Frontdoor

Replace only the Redis transport. Use `MockAsyncRedis` from `tests/helpers/mock_redis.py` at the `redis.asyncio.from_url` boundary. Do not patch the consumer.

```python
import pytest
import redis.asyncio
from fastapi.testclient import TestClient

from tests.helpers.mock_redis import MockAsyncRedis


@pytest.fixture
def redis_double(monkeypatch: pytest.MonkeyPatch) -> MockAsyncRedis:
    double = MockAsyncRedis()
    monkeypatch.setattr(redis.asyncio, "from_url", lambda *_a, **_k: double)
    return double


def test_orders_consumer_is_running(redis_double: MockAsyncRedis) -> None:
    with TestClient(app) as client:
        assert client.get("/healthz").json()["consumers"] == {"orders": "running"}
```

Publish with `RedisStreamsEventBus(client=redis_double).publish_event(...)`. Assert on the public route or on `redis_double.streams`. Do not call the handler directly.

## Behavior Reference

| Situation | Result |
|---|---|
| Consumer group creation fails | `start()` raises. The service does not start. |
| Handler returns | Message acknowledged. `processed_count` increases. |
| Handler raises | `{stream}.dlq` receives the message with `error_reason`. Message acknowledged. `dead_letter_count` increases. |
| Read raises | Error logged at `ERROR`. `status` is `failed` until a read succeeds. The loop retries with backoff. |
| Loop task dies | `status` is `failed`. |

## Related

- [Redis Streams Event Bus Reference](../reference/redis-streams-event-bus.md): production consumers and removed consumer decisions.
- [Define Event-Sourced Aggregates](define-event-sourced-aggregates.md): where domain events come from.
