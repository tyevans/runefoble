# ADR-0006: Redis Streams as the High-Throughput Event Broker for Bounded Contexts

## Context

Runefoble services communicate through both synchronous HTTP request/response queries and asynchronous domain event streaming:
- In-memory event passing fails when services scale horizontally across multiple Kubernetes pods.
- Heavyweight enterprise messaging brokers (such as Kafka) introduce substantial operational complexity and high memory footprints in local Kind clusters.
- Low-latency voice-to-intent and board updates demand sub-50ms message propagation with consumer group acknowledgments (`XACK`), pending entries lists (`XPENDING`), and replayability.

## Decision

We adopt **Redis Streams** as the foundational asynchronous event broker connecting all bounded contexts:

1. **Stream Partitioning by Domain Topic**:
   - `runefoble.events.session`: Session lifecycle, turns, player presence, initiative order.
   - `runefoble.events.board`: Token positioning, movements, fog-of-war mutations.
   - `runefoble.events.watcher`: Spoken intent transcripts, DM rulings, stand-in actions.
   - `runefoble.events.character`: Character HP updates, condition additions, session penalties.
2. **CloudEvents Payload Encapsulation**:
   Every message written via `XADD` holds a JSON payload strictly adhering to `BaseRunefobleEvent` (`id`, `timestamp`, `campaign_id`, `session_id`, `event_type`, `data`).
3. **Consumer Groups**:
   Services register dedicated consumer groups (e.g. `board-animator-group`, `watcher-intelligence-group`, `gateway-websocket-fanout`) utilizing `XREADGROUP` to guarantee load-balanced, at-least-once delivery with explicit acknowledgment.
4. **Fallback Interface**:
   `libs/runefoble_platform` provides an abstract `EventBus` protocol with two concrete implementations: `RedisStreamsEventBus` for production/cluster deployment, and `InMemoryEventBus` for isolated unit tests.

## Consequences

- Ultra-low latency pub/sub (< 5ms) suitable for real-time speech and board synchronization.
- Ephemeral Kind cluster footprints remain lightweight without sacrificing enterprise delivery guarantees.
- Events can be replayed from any offset ID for debugging or session reconstructions.
