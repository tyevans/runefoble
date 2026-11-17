# Reference: Redis Streams Event Bus & Consumer Groups

Runefoble uses Redis Streams as a high-throughput, distributed event bus for cross-service asynchronous communication, projection workers, and real-time synchronization.

## Architecture Overview

```
                      +-----------------------------+
                      |   Domain Event Publisher    |
                      |   (RedisStreamsEventBus)   |
                      +--------------+--------------+
                                     | XADD
                                     v
                       [ Redis Stream: events.session ]
                                     |
          +--------------------------+--------------------------+
          | XREADGROUP (Group: session_workers)                 |
          v                                                     v
+-----------------------+                             +-----------------------+
|   Consumer Worker 1   |                             |   Consumer Worker 2   |
| (SessionReadProjection)|                             | (SessionReadProjection)|
+-----------+-----------+                             +-----------+-----------+
            |                                                     |
    Success | XACK                                        Failure | (After retries)
            v                                                     v
   (PEL Cleared)                                     [ DLQ: events.session.dlq ]
                                                     + XACK original stream
```

### Components

1. **`RedisStreamsEventBus` (`libs/runefoble_platform/redis_bus.py`)**:
   - Publishes domain events, Pydantic models, or structured dictionaries to Redis Streams using `XADD`.
   - Serializes events into `event_type`, `event_id`, and JSON payload fields.
   - `publish_event(stream, event)` is the only publish method. No `publish` method exists.

2. **`RedisConsumerGroup` & `deserialize_event` (`libs/runefoble_platform/consumer_group.py`, `event_deserializer.py`)**:
   - `RedisConsumerGroup` (aliased as `RedisConsumerGroupWorker`) manages consumer group lifecycles (`create_group`, `read_group`, `ack`, `auto_claim_pending`, `route_to_dead_letter`).
   - `deserialize_event` (`event_deserializer.py`) provides isolated deserialization and CloudEvents/DomainEvent registry resolution with W3C trace context preservation (`traceparent`, `tracestate`).
   - `MockAsyncRedis` (`mock_redis.py`) provides in-memory mock Redis Streams and Consumer Group operations for hermetic testing.
   - Implements competing consumer distribution across horizontally scaled service replicas.
   - Recovers unacknowledged/stuck messages from failed or stalled workers using `XAUTOCLAIM`.
   - Isolates poison pill messages to Dead Letter Queues (`{stream}.dlq`) with failure metadata.

3. **`SessionReadProjection` & Sub-Projections (`services/game_session/projections/`)**:
   - Sub-packaged projection workers subscribing to session event streams.
   - `InitiativeProjection` (`projections/initiative.py`): tracks turn order, round cycling, and initiative snapshots.
   - `PresenceProjection` (`projections/presence.py`): tracks participant presence, standby flags, and hot-swap handoffs.
   - `apply_session_event` (`projections/appliers.py`): applies token, atmosphere, encounter, and turn state changes.
   - `SessionReadProjection` (`projections/session.py`): composes projections into comprehensive session read models (`SessionReadModel`, `TokenReadModel`, `AtmosphereReadModel`, `EncounterReadModel`).
   - Re-exported via `services/game_session/projections/__init__.py` for backward compatibility.

---

## Publishing Events

Call `publish_event(stream, event)` on `RedisStreamsEventBus` for every event. Do not call `publish`. A call to `publish` raises `AttributeError`. A broad exception guard around that call hides the error, so the event never reaches Redis. Do not wrap publish calls in `contextlib.suppress(Exception)`.

### Board Events

Board State publishes every uncommitted event through one helper, `publish_board_events(bus, events)` (`services/board_state/src/board_state/events.py`):

```python
events = list(board.uncommitted_events)  # capture before the save clears them
await repo.save(board)
bus = get_event_bus()
if bus is not None:
    await publish_board_events(bus, events)
```

- Events publish in order to the `runefoble.events.board` stream.
- The helper calls `publish_or_fail`. On failure it logs the stream and event type, counts the failure, and raises `DomainEventPublishError`. The route returns HTTP 503.
- Capture the events before `repo.save`. The save marks them committed and clears the list.

### Watcher Events

The Watcher publishes to `runefoble.events.watcher` and to `runefoble:events:world` (turf war, `STREAM_WORLD`) with `publish_event(STREAM, event)`. Each call goes through the publish failure policy below.

### Publish Failure Policy

Every publish call uses one of two helpers from `runefoble_platform.event_publish`. Neither helper suppresses an error silently.

| Helper | Use for | On failure |
|---|---|---|
| `publish_or_fail(bus, stream, event)` | Routes that change state, and DM decisions | Logs at error level, counts the failure, raises `DomainEventPublishError`. The app returns HTTP 503. |
| `publish_best_effort(bus, stream, event)` | Read-model updates, projections, recaps, and suggestions | Logs at error level and counts the failure. Returns `False`. The request still succeeds. |

`deliver_best_effort(destination, event_type, awaitable)` applies the best-effort policy to WebSocket broadcasts and the in-memory platform bus.

Rules for clients and operators:

- A 503 means the audit event was not published. The state change may already be saved. Retry the request. Retried create requests can produce a second record, so check for duplicates.
- `publish_or_fail` routes call the engine or save the aggregate only after the event is built. Veto, approve, and modify publish the event from a planned copy first. A failed publish leaves the pending action unchanged.
- Each service exposes `event_publish_failures` (a count) on `/healthz`. Watch this value. A rising count means events are being lost.
- Services that map 503 call `install_publish_failure_handler(app)` in their `main.py`.

Decision routes that return 503 include the Watcher veto, approve, modify, DM whisper, stand-in activation, and autonomous DM routes. Game session routes that return 503 include session start, hot-swap takeover, combat, tavern, bounty, campfire, caravan, stronghold, settlement, and west marches routes. The dice roll route in game session uses `publish_best_effort` until TASK-0565 refactors it.

---

## Consumer Group Operations

### Group Creation
```python
await consumer_group.create_group(
    stream="runefoble.events.session",
    group_name="session_projection_workers",
    start_id="0",
    make_stream=True,
)
```
- Creates stream and consumer group if absent (`mkstream=True`).
- Idempotent: returns `True` if created, `False` if `BUSYGROUP` is caught.
- Any other error propagates. A broken stream or Redis error stops start-up.

#### Inference Worker Start-Up

`RedisInferenceConsumer.start()` (`services/inference_worker/src/inference_worker/redis_consumer.py`) follows the same rule. It catches `ResponseError` only when the message contains `BUSYGROUP`. `WRONGTYPE`, connection errors, and other errors raise from `start()`.

### Event Bus Selection at Start-Up

`get_event_bus()` (`libs/runefoble_platform/src/runefoble_platform/event_sourcing.py`) returns `RedisEventBus` when the Redis flag is set. It returns `InMemoryEventBus` only when the flag is off. A failure while it creates the Redis bus raises. No in-memory bus replaces it.

### Competing Consumer Reading
```python
messages = await consumer_group.read_group(
    stream="runefoble.events.session",
    group_name="session_projection_workers",
    consumer_name="worker_pod_1",
    count=10,
    block_ms=2000,
)
```
- Reads using `XREADGROUP GROUP <group> <consumer> COUNT <count> BLOCK <block_ms> STREAMS <stream> >`.
- Automatically deserializes payloads into corresponding `DomainEvent` subclasses.
- Each message is delivered to exactly one active consumer in the group, enabling horizontal load balancing.

### Acknowledgment (ACK)
```python
await consumer_group.ack(
    stream="runefoble.events.session",
    group_name="session_projection_workers",
    message_ids="1700000000000-1",
)
```
- Removes processed message IDs from the stream's Pending Entries List (PEL) via `XACK`.
- Accepts either a single message ID or a list of message IDs.

### Pending Message Auto-Claiming
```python
claimed = await consumer_group.auto_claim_pending(
    stream="runefoble.events.session",
    group_name="session_projection_workers",
    consumer_name="worker_pod_1",
    min_idle_ms=60000,
    count=10,
)
```
- Scans PEL using `XAUTOCLAIM` for messages unacknowledged longer than `min_idle_ms`.
- Automatically transfers ownership to the claiming consumer, preventing stuck messages when a worker pod crashes.

### Dead Letter Queue (DLQ) Fallback
```python
dlq_id = await consumer_group.route_to_dead_letter(
    stream="runefoble.events.session",
    message_id="1700000000000-1",
    payload=raw_payload,
    error_reason="ValidationError: Corrupted payload structure",
    max_retries=3,
)
```
- Publishes poison pill events to `{stream}.dlq` via `XADD`.
- Attached metadata envelope:
  - `original_stream`: Stream where failure occurred.
  - `original_message_id`: Redis message ID in original stream.
  - `payload`: Serialized event payload.
  - `error_reason`: Exception message or stack summary.
  - `max_retries`: Configured retry threshold before quarantine.
  - `failed_at`: ISO 8601 UTC timestamp.
  - `event_type`: `"DeadLetterEvent"`.

---

## Event Projection Workers

`SessionReadProjection` maintains denormalized views of tactical boards and active encounters:

```python
from game_session.projections import SessionReadProjection
from runefoble_platform.consumer_group import RedisConsumerGroup

consumer_group = RedisConsumerGroup(redis_url="redis://localhost:6379/0")
projection = SessionReadProjection(
    consumer_group=consumer_group,
    stream="runefoble.events.session",
    group_name="session_projection_workers",
    consumer_name="worker_1",
)

# Start background async loop
await projection.start()

# Query denormalized state
session_view = projection.get_session("session-uuid")
tokens = projection.get_tokens("session-uuid")
atmosphere = projection.get_atmosphere("session-uuid")
encounters = projection.get_encounters("session-uuid")

# Gracefully terminate
await projection.stop()
```

### Projected Events
- `TokenPlaced`, `TokenMoved`, `TokenRemoved`: Spatial grid token coordinates and status.
- `SceneAtmosphereSet`: Scene lighting, mood, audio ambience prompts.
- `EncounterSpawned`: Active encounters, monster rosters, tactical objectives.
- `AutonomousActionResolved`: Append-only combat action log.
- `TurnAdvanced`: Active turn index.
- `SessionStarted`, `SessionEnded`: Session lifecycle status (`lobby`, `active`, `ended`).

---

## Testing & Verification

The Redis Streams event bus, consumer groups, and read projections are verified by dedicated integration test suites:

- **`tests/test_redis_consumer_groups.py`**: Low-level distributed consumer group mechanics, competing consumers, PEL acknowledgements, `XAUTOCLAIM` recovery, and DLQ dispatching.
- **`tests/test_session_projections.py`**: High-level `SessionReadProjection` worker event processing, read model state transitions, and poison pill DLQ isolation.
- **`tests/test_blackbox_publish_failure_policy.py`**: Verifies that decision routes return 503 with the pending action unchanged, and that side-effect publish failures are counted on `/healthz`.
- **`tests/test_blackbox_board_event_publish.py`**: Verifies board and watcher events reach the Redis stream through `publish_event`.
- **`tests/test_game_session_projections.py`**: Modular projection lifecycle tests covering `InitiativeProjection`, `PresenceProjection`, tie-breaking rules, and participant presence tracking.

