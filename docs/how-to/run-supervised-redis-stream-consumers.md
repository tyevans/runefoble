# How-To: Run Supervised Redis Stream Consumers

Use this recipe when a service must read a Redis Stream. The helpers live in `runefoble_platform.stream_consumer`. Each service starts its consumers in its FastAPI lifespan and reports them on `/healthz`.

## Rules

1. One start point. Build the consumer set and start it in the lifespan. Do not start a loop at import time.
2. Start-up fails loudly. `SupervisedStreamConsumers.start()` raises when a consumer group cannot be created. Do not catch that error.
3. Acknowledge after success. The handler runs first. The message is acknowledged only when the handler returns.
4. Dead-letter failures. A handler that raises routes the message to `{stream}.dlq`, then acknowledges it. The original message does not stay pending.
5. Report runtime failures. A failed read loop is logged at `ERROR`. Its `status` becomes `failed`. Publish the status on `/healthz`.
6. Reclaim abandoned messages. A consumer takes over a message that another consumer read and did not acknowledge. A reclaimed message runs its handler again, so every handler must be idempotent (see below).

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

## Step 3: Tune Reclaim

Each `StreamConsumer` reclaims stale pending messages on its read loop. Two settings in `PlatformSettings` control it:

| Setting | Environment variable | Default | Meaning |
|---|---|---|---|
| `consumer_reclaim_min_idle_ms` | `RUNEFOBLE_CONSUMER_RECLAIM_MIN_IDLE_MS` | `60000` | A pending message is reclaimed after this idle time. |
| `consumer_reclaim_every_polls` | `RUNEFOBLE_CONSUMER_RECLAIM_EVERY_POLLS` | `50` | A consumer checks for reclaimable messages once every this many polls. |

Pass `reclaim=ReclaimPolicy(min_idle_ms=..., every_polls=...)` to `StreamConsumer` to use other values in one consumer. Without it, the consumer reads the settings. The policy cannot be turned off.

**Slow-handler risk.** A message stays pending while its handler runs. If the handler runs longer than `min_idle_ms`, another consumer reclaims the message while the handler still runs. Both runs then reach the handler. Set `min_idle_ms` above the longest handler run. Keep handlers idempotent so that an overlap does no harm.

**Undecodable messages.** A reclaimed message that cannot be decoded goes to `{stream}.dlq` and is acknowledged. It does not raise, and no handler runs for it.

## Step 4: Write Idempotent Handlers

A handler can receive the same message twice. Use one of these guards before it writes:

1. **State guard.** Read the aggregate state. Skip the write when the state already holds the result. Store the source id in the state when the result alone does not identify the source. Examples: the session stores `weather_source_proposal_id`, the board stores `forged_asset_id`, and the session keeps the last 1,000 board `TokenMoved` ids that its chronicle recorded (`chronicled_move_ids`).
2. **Source ledger.** When no state guard fits, record the source event id in the aggregate in the same save as the effect. Skip an event whose id is already recorded. The soundscape aggregate does this. It keeps the last 1,000 source event ids per session, so a redelivery older than that window applies again.

Save the effect and its guard in one write. A crash between two writes can apply one and lose the other.

## Step 5: Test Through the Frontdoor

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
| Message pending longer than `consumer_reclaim_min_idle_ms` | Reclaimed on a reclaim check. The handler runs, then the message is acknowledged. |
| Reclaimed message cannot be decoded | Routed to `{stream}.dlq` and acknowledged. No handler runs. |

## Related

- [Redis Streams Event Bus Reference](../reference/redis-streams-event-bus.md): production consumers and removed consumer decisions.
- [Define Event-Sourced Aggregates](define-event-sourced-aggregates.md): where domain events come from.
