# ADR-0007: Domain-Driven Design (DDD) Layering and Ubiquitous Language

## Context

Virtual tabletop platforms are prone to "anemic domain model" antipatterns where database schemas leak directly into controllers, creating brittle spaghetti code where game physics, networking, and UI logic mix unchecked.
As Runefoble introduces AI autonomy, multiple microservices must preserve strict invariant boundaries around encounters, combat turns, spatial positioning, and character states.

## Decision

We adopt strict **Domain-Driven Design (DDD)** principles across all bounded contexts:

1. **Layer Separation**:
   - **Domain Layer (`domain/`)**: Pure business logic, Aggregate Roots, Entities, Value Objects, and Domain Events. Has ZERO dependencies on web frameworks (FastAPI), databases, or ORMs.
   - **Application Layer (`application/`)**: Use-case orchestration, command/query handlers, and transaction coordination.
   - **Infrastructure Layer (`infrastructure/`)**: External adapters (Postgres repositories, Redis Streams producers/consumers, SpiceDB clients, HTTP clients).
   - **Presentation / Interface Layer (`interfaces/` or `main.py`)**: FastAPI routers, WebSocket handlers, and CLI entrypoints.
2. **Aggregate Roots as Invariant Guardians**:
   - `GameSession`: Guarantees initiative rotation and round boundaries cannot be skipped or duplicated.
   - `TacticalBoard`: Enforces coordinate grid boundaries, collision rules, and token ownership.
   - `Character`: Protects HP bounds (`0 <= current_hp <= max_hp`) and validates condition applications.
   - `WatcherSession`: Manages the conversational context buffer and stand-in behavior rules.
3. **Ubiquitous Language**:
   Every BC defines a shared vocabulary document preventing semantic drift (e.g. distinguishing an *Encounter* from a *Session*, and a *Token* from a *Character*).
4. **Primary Communication Interfaces**:
   - **Synchronous Inbound**: HTTP REST APIs documenting OpenAPI 3.1 contracts for commands and queries.
   - **Asynchronous Outbound/Inbound**: Redis Streams for domain events.

## Consequences

- Domain logic is 100% unit-testable in pure Python without mocking database connections.
- Storage engines can change from PostgreSQL to other stores without altering domain rules.
- Cognitive load is isolated within bounded context perimeters.
