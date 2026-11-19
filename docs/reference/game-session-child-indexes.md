# Reference: Game Session Child Indexes

The game session service lists child aggregates under a parent. Examples are bounties under a session, and establishments under a settlement. The parent-to-child links are event-sourced. They are not kept in process memory.

Source:

- `services/game_session/src/game_session/shared/child_index.py`: the aggregate and the stream id. This is the mechanism of the shared kernel (ADR-0021 D2).
- `services/game_session/src/game_session/shared/child_index_queries.py`: `link_child`, `list_child_ids`, and the index repository.
- The kinds and the read functions of each domain: `settlement/child_indexes.py`, `caravan/child_indexes.py`, and `contracts/child_indexes.py`.
- `libs/runefoble_events/src/runefoble_events/child_index.py`: the event.

## Approach

Each parent and kind pair has one index stream in the event store. The stream is a `ChildIndexAggregate`. It holds the child ids in link order. The mechanism accepts the kind as a string. It does not know the kinds of the domains.

- The stream id is `uuid5` of `<kind>:<parent id>`. The id is deterministic, so no lookup table is needed.
- Each link is one `runefoble.events.game_session.child_linked` event. Linking the same child again emits no event.
- The index is saved through the aggregate repository. It is not published to a Redis stream.
- A missing index stream means an empty list.

A store outage raises to the caller. The service returns `503 Service Unavailable` (see [Redis Streams Event Bus](redis-streams-event-bus.md) and ADR-0015 f).

## Index Kinds

| Kind | Declared in | Parent | Child | Read function |
|---|---|---|---|---|
| `session_bounties` | `contracts/child_indexes.py` (`SESSION_BOUNTIES`) | Session id | Bounty id | `list_bounties_for_session` |
| `world_contracts` | `caravan/child_indexes.py` (`WORLD_CONTRACTS`) | Shared world id | Caravan contract id | `list_world_contracts_for_world` |
| `settlement_establishments` | `settlement/child_indexes.py` (`SettlementChildIndex`) | Settlement id | Establishment id | `list_establishments_for_settlement` |
| `campaign_settlements` | `settlement/child_indexes.py` (`SettlementChildIndex`) | Campaign id | Settlement id | `list_settlements_for_campaign` |
| `establishment_workers` | `settlement/child_indexes.py` (`SettlementChildIndex`) | Establishment id | NPC worker id | `list_workers_for_establishment` |
| `establishment_negotiations` | `settlement/child_indexes.py` (`SettlementChildIndex`) | Establishment id | Negotiation id | None. No list route reads it yet. |

## Write Order

A router saves the child aggregate first. It then calls `link_child(kind, parent_id, child_id)`. If the child save fails, no link is written. If the link write fails after the save, the request fails with an error. The child is saved but not listed.

## Read Behaviour

- A list query loads each child with `load_if_exists`. A child whose stream is missing is skipped.
- Any other load error propagates. The query does not return a partial list.
- Two first links to the same parent at the same time can conflict on the stream version. One request then fails. No link is lost silently.

## Persistence

The index streams live in the same event store as the other game session aggregates. With the PostgreSQL event store, the links survive a restart of the service.
