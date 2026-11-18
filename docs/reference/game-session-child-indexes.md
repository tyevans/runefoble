# Reference: Game Session Child Indexes

The game session service lists child aggregates under a parent. Examples are bounties under a session, and establishments under a settlement. The parent-to-child links are event-sourced. They are not kept in process memory.

Source: `services/game_session/src/game_session/child_index.py` (aggregate and kinds), `services/game_session/src/game_session/queries/child_index.py` (read and write functions), and `libs/runefoble_events/src/runefoble_events/child_index.py` (event).

## Approach

Each parent and kind pair has one index stream in the event store. The stream is a `ChildIndexAggregate`. It holds the child ids in link order.

- The stream id is `uuid5` of `<kind>:<parent id>`. The id is deterministic, so no lookup table is needed.
- Each link is one `runefoble.events.game_session.child_linked` event. Linking the same child again emits no event.
- The index is saved through the aggregate repository. It is not published to a Redis stream.
- A missing index stream means an empty list.

A store outage raises to the caller. The service returns `503 Service Unavailable` (see [Redis Streams Event Bus](redis-streams-event-bus.md) and ADR-0015 f).

## Index Kinds

| Kind (`ChildIndexKind`) | Parent | Child | Read function |
|---|---|---|---|
| `session_bounties` | Session id | Bounty id | `list_bounties_for_session` |
| `world_contracts` | Shared world id | Caravan contract id | `list_world_contracts_for_world` |
| `settlement_establishments` | Settlement id | Establishment id | `list_establishments_for_settlement` |
| `campaign_settlements` | Campaign id | Settlement id | `list_settlements_for_campaign` |
| `establishment_workers` | Establishment id | NPC worker id | `list_workers_for_establishment` |
| `establishment_negotiations` | Establishment id | Negotiation id | None. No list route reads it yet. |

## Write Order

A router saves the child aggregate first. It then calls `link_child(kind, parent_id, child_id)`. If the child save fails, no link is written. If the link write fails after the save, the request fails with an error. The child is saved but not listed.

## Read Behaviour

- A list query loads each child with `load_if_exists`. A child whose stream is missing is skipped.
- Any other load error propagates. The query does not return a partial list.
- Two first links to the same parent at the same time can conflict on the stream version. One request then fails. No link is lost silently.

## Persistence

The index streams live in the same event store as the other game session aggregates. With the PostgreSQL event store, the links survive a restart of the service.
