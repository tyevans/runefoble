# ADR-0011: eventsource-py as Core Event Sourcing and Aggregate Engine

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

## Amendment (2026-11-17, TASK-0707)
Decision point 4 changes. ADR-0015 forbids silent fallbacks, so the event store is no longer chosen
by environment type:
- `RUNEFOBLE_EVENT_STORE_BACKEND` selects the store. The default is `postgresql`.
- `memory` selects `InMemoryEventStore`. Only the test configuration and a developer who sets it by
  name use it.
- A service in a `staging` or `production` environment refuses `memory` at start-up with
  `EventStoreInitializationError`.

## Amendment (2026-11-18, TASK-0772): Commands across two aggregates
`AggregateRepository.save` appends to one stream. The library gives no atomic save across two
aggregates. A command that changes two aggregates therefore uses a process manager:

1. **Commit the decision first.** The command records its decision and outcome on the owning
   aggregate, and saves that aggregate. This save is the commit point. Example: the crafting
   aggregate records a combine attempt, its outcome, and the damage it deals.
2. **Apply the outcome to the other aggregate, once.** The other aggregate applies the recorded
   outcome. It records an applied marker that names the source event id (for example
   `CharacterCraftingOutcomeApplied` with `crafting_event_id`). The effects and the marker share
   one save of that aggregate, so the apply is all or nothing.
3. **Make the apply idempotent.** The applied set on the target aggregate blocks a second apply
   of the same source event. A retry never applies an effect twice.
4. **Recover pending outcomes.** When step 2 fails, the request answers `503`. The outcome stays
   pending. Every later command on the target aggregate, and every read that a route marks for
   recovery, applies pending outcomes first. Pending means: the decision has an outcome event, the
   target has not applied it, and the record opted into the process manager.
5. **Let clients retry safely.** A command that a client can repeat carries an optional client
   attempt id. The decision records it. A repeat with the same id returns the recorded outcome and
   records nothing new. A command without an id is always a new decision.
6. **Record old data as not pending.** Events written before the pattern default to the value
   that means "no apply needed", so the recovery pass never re-applies them.

Trade-offs: a client can see a `503` after the decision is saved. The recorded decision then
takes effect later, on the next command or read. Event publishing happens after each save. A
publish failure does not undo a save. This is the same best-effort rule as TASK-0729.

Applied to: `CombineReagentsService` in `services/character_sheet` (crafting decision, then
character effects). See `docs/how-to/run-campfire-rests-and-alchemical-crafting.md`.
