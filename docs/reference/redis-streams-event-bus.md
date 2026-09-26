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

2. **`RedisConsumerGroup` (`libs/runefoble_platform/consumer_group.py`)**:
   - Manages consumer group lifecycles (`create_group`, `read_group`, `ack`, `auto_claim_pending`, `route_to_dead_letter`).
   - Implements competing consumer distribution across horizontally scaled service replicas.
   - Automatically deserializes stream entries into registered `DomainEvent` classes via `deserialize_event`.
   - Recovers unacknowledged/stuck messages from failed or stalled workers using `XAUTOCLAIM`.
   - Isolates poison pill messages to Dead Letter Queues (`{stream}.dlq`) with failure metadata.

3. **`SessionReadProjection` (`services/game_session/projections.py`)**:
   - Background event projection worker subscribing to session event streams.
   - Maintained in-memory / cache-accelerated denormalized read models (`SessionReadModel`, `TokenReadModel`, `AtmosphereReadModel`, `EncounterReadModel`).
   - Supports graceful shutdown and poison pill fault isolation.

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

