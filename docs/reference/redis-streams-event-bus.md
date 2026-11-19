# Reference: Redis Streams Event Bus & Consumer Groups

Runefoble uses Redis Streams as a high-throughput, distributed event bus for cross-service asynchronous communication. Four services run stream consumers in production today: Campaign Analytics, Soundscape, Board State, and Game Session. See [Production Consumers](#production-consumers).

## Architecture Overview

```
                      +-----------------------------+
                      |   Domain Event Publisher    |
                      |   (RedisStreamsEventBus)   |
                      +--------------+--------------+
                                     | XADD
                                     v
                       [ Redis Stream: runefoble.events.session ]
                                     |
          +--------------------------+--------------------------+
          | XREADGROUP (Group: <service>_workers)               |
          v                                                     v
+-----------------------+                             +-----------------------+
|  Replica 1 (consumer) |                             |  Replica 2 (consumer) |
|  StreamConsumer       |                             |  StreamConsumer       |
+-----------+-----------+                             +-----------+-----------+
            |                                                     |
    Success | XACK                                        Failure | (handler raises)
            v                                                     v
   (PEL Cleared)                                     [ DLQ: runefoble.events.session.dlq ]
                                                     + XACK original stream
```

### Components

1. **`RedisStreamsEventBus` (`libs/runefoble_platform/src/runefoble_platform/redis_bus.py`)**:
   - Publishes domain events, Pydantic models, or structured dictionaries to Redis Streams using `XADD`.
   - Serializes events into `event_type`, `event_id`, and JSON payload fields.
   - `publish_event(stream, event)` is the only publish method. No `publish` method exists.

2. **`RedisConsumerGroup` & `deserialize_event` (`libs/runefoble_platform/src/runefoble_platform/consumer_group.py`, `event_deserializer.py`)**:
   - `RedisConsumerGroup` manages consumer group lifecycles (`create_group`, `read_group`, `ack`, `auto_claim_pending`, `route_to_dead_letter`).
   - `deserialize_event` (`event_deserializer.py`) provides isolated deserialization and CloudEvents/DomainEvent registry resolution with W3C trace context preservation (`traceparent`, `tracestate`).
   - `deserialize_event` returns a registered `DomainEvent`, or an `UnknownEvent` for an unregistered type. It raises `EventDecodeError` for every other input. See [Decode Rules](#decode-rules).
   - `MockAsyncRedis` is a test double in `tests/helpers/mock_redis.py`. Production code must not import it.
   - Implements competing consumer distribution across horizontally scaled service replicas.
   - Recovers unacknowledged/stuck messages from failed or stalled workers using `XAUTOCLAIM`.
   - Isolates poison pill messages to Dead Letter Queues (`{stream}.dlq`) with failure metadata.

3. **`StreamConsumer`, `SupervisedStreamConsumers` (`libs/runefoble_platform/src/runefoble_platform/stream_consumer.py`)**:
   - One consumer reads one stream for one group. It acknowledges a message only after its handler returns.
   - The handler receives `(message_id, payload)`. A consumer may resume its group from a position that the service stored, using `XGROUP SETID`.
   - A handler failure routes the message to `{stream}.dlq`, then acknowledges it.
   - An undecodable message routes to `{stream}.dlq` and is acknowledged before any handler runs.
   - A set of consumers starts as one unit. Start-up raises when a consumer group cannot be created.
   - `status` is `running` while every read loop lives and the last read succeeded. Otherwise it is `failed`.
   - How-to: [Run Supervised Redis Stream Consumers](../how-to/run-supervised-redis-stream-consumers.md).

4. **Projection status**: Three kinds of projection exist. All three run in production.
   - **Running, Redis Streams**: the `analytics` consumer in `campaign_analytics` (`CampaignAnalyticsWorker.handle_event`) updates the analytics read models. See [Production Consumers](#production-consumers).
   - **Running, rebuilt at start-up**: the Campaign Lore retrieval projection (`services/campaign_lore/src/campaign_lore/projection.py`). `rebuild_lore_projection` replays `LoreDocument` events from the PostgreSQL event store in the service lifespan. The retrieval engine is held in process memory and is rebuilt on each start.
   - **Running, rebuilt at start-up**: the Rules Compendium homebrew index (`services/rules_compendium/src/rules_compendium/projection.py`). `rebuild_homebrew_projection` replays `runefoble.events.compendium.homebrew_rule_registered` events from the event store in the service lifespan. The index serves search and monster lookup. The list route reads the campaign aggregate.

---

## Publishing Events

### Stream Naming Rule

Every stream uses the dotted form `runefoble.events.<bc>`, where `<bc>` is the owning bounded context (for example `session`, `board`, `watcher`, `world`, `system`, `asset`, `character`). Stream names never use colons. A stream that carries events from one bounded context uses that context's name. Entries that a producer writes to a stream it does not own are a defect.

Migration note: the colon names `runefoble:events:world` and `runefoble:events:system` are removed. Producers write to `runefoble.events.world` and `runefoble.events.system`. Entries in the old streams are not copied. A stream reader must read the dotted name.

Asset Forge publishes `PortraitVariantGenerated` to `runefoble.events.character`, the stream that Character Sheet and its consumers read. It publishes every other forge event to `runefoble.events.asset`.

Call `publish_event(stream, event)` on `RedisStreamsEventBus` for every event. Do not call `publish`. A call to `publish` raises `AttributeError`. A broad exception guard around that call hides the error, so the event never reaches Redis. Do not wrap publish calls in `contextlib.suppress(Exception)`.

### Aggregate Event Publication

Routers do not publish events that an aggregate commits. The `AggregateRepository` publishes every committed event through its event publisher.

- The game session repository uses `SessionEventPublisher` (`services/game_session/src/game_session/events.py`).
- `SESSION_EVENT_STREAMS` in the same module maps each session event type to its stream.
- An event type with no mapping raises `UnmappedSessionEventError`. Add the mapping when you add an event.
- A publish failure raises `DomainEventPublishError`. The API returns HTTP 503 and the client retries.
- An event without a type raises `EventTypeMissingError` before any `XADD`. The reader is `event_type_of` in `runefoble_platform.event_fields`. No placeholder type is written.
- A missing bus skips publication, as the other game session routes do when Redis is not configured.

### Board Events

Board State publishes every uncommitted event through one helper, `publish_board_events(bus, events)` (`services/board_state/src/board_state/events.py`):

```python
events = list(board.uncommitted_events)  # capture before the save clears them
await repo.save(board)
bus = get_event_bus()
await publish_board_events(bus, events)
```

- Events publish in order to the `runefoble.events.board` stream.
- The helper calls `publish_or_fail`. On failure it logs the stream and event type, counts the failure, and raises `DomainEventPublishError`. The route returns HTTP 503.
- Capture the events before `repo.save`. The save marks them committed and clears the list.

### Watcher Events

The Watcher publishes to `runefoble.events.watcher` and to `runefoble.events.world` (turf war, `STREAM_WORLD`) with `publish_event(STREAM, event)`. Each call goes through the publish failure policy below.

### Publish Failure Policy

Every publish call uses one of two helpers from `runefoble_platform.event_publish`. Neither helper suppresses an error silently.

| Helper | Use for | On failure |
|---|---|---|
| `publish_or_fail(bus, stream, event)` | Routes that change state, and DM decisions | Logs at error level, counts the failure, raises `DomainEventPublishError`. The app returns HTTP 503. |
| `publish_best_effort(bus, stream, event)` | Read-model updates, projections, recaps, and suggestions | Logs at error level and counts the failure. Returns `False`. The request still succeeds. |

`deliver_best_effort(destination, event_type, awaitable)` applies the best-effort policy to any delivery that is not a bus publish, such as a WebSocket broadcast or a board fan-out. No in-process event bus exists.

Rules for clients and operators:

- A 503 means the audit event was not published. The state change may already be saved. Retry the request. Retried create requests can produce a second record, so check for duplicates.
- `publish_or_fail` routes call the engine or save the aggregate only after the event is built. Veto, approve, and modify publish the event from a planned copy first. A failed publish leaves the pending action unchanged.
- Each service exposes `event_publish_failures` (a count) on `/healthz`. Watch this value. A rising count means events are being lost. The count covers every failed delivery, so one event sent to two streams can add two.
- Services that map 503 call `install_publish_failure_handler(app)` in their `main.py`.

Decision routes that return 503 include the Watcher veto, approve, modify, DM whisper, stand-in activation, and autonomous DM routes. Game session routes that return 503 include session start, hot-swap takeover, combat, tavern, bounty, campfire, caravan, stronghold, settlement, and west marches routes. The dice roll route in game session uses `publish_best_effort` until TASK-0565 refactors it.

#### Site Classes in Voice Agent

Each publish site in these services belongs to one class.

| Site | Class | Helper | On failure |
|---|---|---|---|
| `POST /api/v1/voice/transcribe` player speech (`runefoble.events.watcher.player_spoke`) | Domain state | `publish_or_fail` | 503. The Watcher is not called. |
| `POST /api/v1/voice/stream/chunk` and stream WebSocket player speech | Domain state | `publish_or_fail` | HTTP 503. On the WebSocket, a `{"status": "publish_failed"}` frame. The chunk is not kept. |
| Voice room peer events (`VoicePeerJoined`, `VoicePeerLeft`, mute) | Notification | `publish_best_effort` | Counted. The request succeeds. |
| Voice stream diagnostics (codec adaptation) | Notification | `publish_best_effort` | Counted. The request succeeds. |

The `gateway_mcp` `/healthz` route returns `event_publish_failures`. The gateway_mcp process publishes no domain event.

---

## Production Consumers

Each service starts its consumers in its FastAPI lifespan. A start-up failure stops the service. A runtime failure is logged at `ERROR`, and the service reports it on `/healthz`.

| Consumer name | Service | Streams | Group | Handler | `/healthz` key |
|---|---|---|---|---|---|
| `analytics` | `campaign_analytics` | `runefoble.events.session`, `runefoble.events.board`, `runefoble.events.character`, `runefoble.events.watcher` | `campaign_analytics_worker` | `CampaignAnalyticsWorker.handle_event` (one projection transaction per message, stores the stream position) | `consumers.analytics` |
| `soundscape` | `soundscape` | `runefoble.events.session`, `runefoble.events.watcher`, `runefoble.events.character`, `runefoble.events.board` | `soundscape_workers` | `handle_incoming_domain_event` | `consumers.soundscape` |
| `board_state` | `board_state` | `runefoble.events.asset` | `board_state_workers` | `apply_forged_battlemap_event` (applies `BattlemapForged` layout to the board of its session) | `consumers.board_state` |
| `game_session` | `game_session` | `runefoble.events.audience` | `game_session_workers` | `apply_audience_weather_event` (records `WeatherChanged` for an approved `weather_change` modifier; other modifiers are ignored) | `consumers.game_session` |
| `character_sheet` | `character_sheet` | `runefoble.events.audience` | `character_sheet_workers` | `apply_audience_status_event` (applies a buff condition to the character of an approved `status_buff` modifier; other modifiers are ignored) | `consumers.character_sheet` |

`/healthz` returns `200` with `"status": "ok"` when every consumer is `running`. It returns `503` with `"status": "degraded"` when any consumer is `failed`.

### Removed Consumers and Decisions

These consumers had no running process. TASK-0578 removed them or started them. Each decision below is final for this release.

| Component | Decision | Reason |
|---|---|---|
| `SpiceDBEventListener` | Removed. | No service called `register_bus_handlers`. The listener used the in-process `EventBus`, not Redis Streams. Tuple sync runs through `ZitadelSpiceDBSyncService` on the gateway sync routes (`/api/v1/auth/sync/*`). |
| `RedisInferenceConsumer` (`services/inference_worker`) | Removed. Config keys `RUNEFOBLE_WORKER_REDIS_*` removed. | No producer writes `runefoble.inference.requests`. TASK-0448 may add a producer and a dead-letter path later. |
| `AnalyticsEventWorker` | Removed. | No service started it. OpenPanel forwarding is not deployed. Domain services call `OpenPanelClient` directly if they need it. |
| In-process `runefoble_platform.bus` (`EventBus`) | Deleted (TASK-0710). Every publish goes to Redis Streams. Soundscape handlers run only from the Redis consumer. | Forge and soundscape publishes reached no in-process subscriber. The one subscriber also read the same events from Redis. |
| Gateway MCP dynamic tool bus | Removed with the dynamic tool events (TASK-0703). | The gateway_mcp process has no Redis Streams bus. Its tool calls publish nothing. |

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
- `SupervisedStreamConsumers.start()` calls this for every stream before it starts any read loop.

### Event Bus Selection at Start-Up

### How a Service Gets the Bus

`libs/runefoble_platform/src/runefoble_platform/event_bus.py` holds the only bus factory. No service builds `RedisStreamsEventBus` itself. No in-memory bus exists in production code.

- `create_event_bus(settings)` builds the bus lazily. It raises `EventBusUnavailableError` when `RUNEFOBLE_REDIS_URL` is empty.
- `EventBusUnavailableError` is a `ServiceUnavailableError` from `runefoble_platform.errors`. The one unavailable-error base is `ServiceUnavailableError`.
- `EventBusProvider(settings)` owns one bus per service process. Its methods are `get()`, `set(bus)`, `connect()`, `close()`, and `lifespan(app)`.
- `connect()` pings Redis. It raises `EventBusUnavailableError` when Redis is unreachable.
- `lifespan(app)` is a FastAPI lifespan. It calls `connect()` at start-up and `close()` at shutdown. A service that cannot reach Redis does not start.

Each service `dependencies` module creates one provider and binds its public API:

```python
event_bus_provider = EventBusProvider(platform_settings)
get_event_bus = event_bus_provider.get
set_event_bus = event_bus_provider.set
```

The service `main.py` passes `lifespan=event_bus_provider.lifespan`. A service with its own lifespan calls `event_bus_provider.lifespan(app)` inside it. Tests call `set_event_bus(RedisStreamsEventBus(client=MockAsyncRedis()))`. `close()` does not close a bus that a test set.

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
- Automatically deserializes payloads into corresponding `DomainEvent` subclasses. An undecodable message goes to the DLQ. An unregistered event type reaches the handler as `UnknownEvent`. See [Decode Rules](#decode-rules).
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

### Decode Rules
`deserialize_event` gives one of three outcomes. It never returns raw input.

| Input | Outcome |
|---|---|
| Registered event type, valid payload | Returns the registered `DomainEvent` subclass. |
| Event type with no registered class | Returns `UnknownEvent(event_type, fields)`. `fields` holds the decoded payload object. |
| Anything else (not JSON, payload not a JSON object, no event type, registered type fails validation) | Raises `EventDecodeError`. |

- `read_group` and `auto_claim_pending` catch `EventDecodeError`. They route the message to `{stream}.dlq` with `error_reason` starting `EventDecodeError:`, acknowledge it, and omit it from the result. No handler runs for it.
- `RedisStreamsEventBus.read_group(auto_deserialize=True)` does not catch `EventDecodeError`. The caller receives the exception.

---

## Testing & Verification

The Redis Streams event bus and consumer groups are verified by dedicated integration test suites:

- **`tests/test_redis_consumer_groups.py`**: Low-level distributed consumer group mechanics, competing consumers, PEL acknowledgements, `XAUTOCLAIM` recovery, and DLQ dispatching.
- **`tests/test_blackbox_publish_failure_policy.py`**: Verifies that decision routes return 503 with the pending action unchanged, and that side-effect publish failures are counted on `/healthz`.
- **`tests/test_blackbox_board_event_publish.py`**: Verifies board and watcher events reach the Redis stream through `publish_event`.
- **`tests/test_blackbox_stream_consumers.py`**: Verifies production consumers through service lifespans: projection from a published event, fail-fast start-up, `/healthz` failure reporting, soundscape reaction, and dead-letter routing.

