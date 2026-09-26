# ADR 0011: eventsource-py as Core Event Sourcing and Aggregate Engine

## Status
Accepted

## Date
2026-09-25

## Context
Runefoble is a collaborative, AI-native tabletop roleplaying platform. Game state—including session timelines, initiative turn counters, tactical grid token positions, character health, and DM absence penalties—is inherently chronological, collaborative, and subject to audit, rollback, and real-time multiplayer distribution.

Rather than relying on mutable relational tables or ad-hoc state updates, Runefoble requires a rigorous Event Sourcing and CQRS foundation where:
1. Every state mutation is captured as an immutable, timestamped domain event.
2. State is deterministically reconstituted by replaying events through domain aggregates.
3. Concurrency is handled through optimistic locking (`ExpectedVersion`).
4. Events are registered and serialized across Python services using a robust, production-tested event sourcing library.

The `eventsource-py` package on PyPI (`https://tyevans.github.io/eventsource-py/`, authored by Ty Evans) provides an async-first event sourcing architecture for Python, featuring:
- Standard `DomainEvent` base class with automatic event type derivation and metadata tracking.
- Global `EventRegistry` with decorator `@register_event`.
- `DeclarativeAggregate` with `@handles` decorator for declarative event application.
- `AggregateRepository` coordinating with event stores (`PostgreSQLEventStore`, `InMemoryEventStore`) and event buses (`RedisEventBus`, `InMemoryEventBus`).
- Snapshotting support and subscription projections.

## Decision
We adopt `eventsource-py` as the foundational event sourcing framework across all Runefoble bounded contexts:

1. **Domain Events**: All domain events in `libs/runefoble_events` subclass `eventsource.domain.event.DomainEvent` (via `BaseRunefobleEvent`) and are registered using `@register_event`.
2. **Aggregates**: Microservices implement domain models as subclasses of `eventsource.domain.aggregate.DeclarativeAggregate` with `@handles` event handlers:
   - `GameSessionAggregate` in `services/game_session`
   - `BoardAggregate` in `services/board_state`
   - `CharacterAggregate` in `services/character_sheet`
3. **Persistence & Repositories**: Services persist and reconstitute aggregates using `AggregateRepository` created via `runefoble_platform.event_sourcing.create_aggregate_repository()`.
4. **Event Stores**: In Kubernetes/production environments, events persist to `PostgreSQLEventStore`. In local testing and development environments, `InMemoryEventStore` provides zero-latency ephemeral persistence.
5. **Distribution**: Events are published via `RedisEventBus` or `RedisStreamsEventBus` to notify gateways, WebSockets, and AI services (such as The Watcher and inference workers).

## Consequences
- **Positive**: Complete audit trail of every roll, token move, turn change, and penalty. Time-travel debugging and session replay become native capabilities.
- **Positive**: High resilience against concurrency conflicts via optimistic locking.
- **Positive**: Unified developer experience across all bounded contexts using a cohesive ubiquitous language.
- **Negative**: Developers must maintain strict event immutability and schema versioning when updating event definitions.
