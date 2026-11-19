# How-To: Define Event-Sourced Aggregates with eventsource-py

This guide explains how to define new domain events, state models, and `DeclarativeAggregate` classes in Runefoble using the `eventsource-py` library.

## 1. Define Domain Events

All domain events inherit from `BaseRunefobleEvent` and are registered with the `@register_event` decorator from `runefoble_events.base`. Each event has one wire identifier in the form `runefoble.events.<bc>.<snake_case>`. The identifier never uses the class name.

A class sets its identifier in two places. The decorator registers the identifier. The class field `event_type` sets the value that the event carries. Set `suppress_event_type_warning` to `True` because the class name differs from the identifier:

```python
from typing import ClassVar

from runefoble_events.base import BaseRunefobleEvent, register_event

@register_event("runefoble.events.character.loot_item_acquired")
class LootItemAcquired(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.character.loot_item_acquired"
    aggregate_type: str = "CharacterSheet"
    item_id: str
    item_name: str
    quantity: int = 1
    rarity: str = "common"
```

Run `uv run python scripts/generate_event_catalogue.py` after you add an event. The script fails when an identifier breaks the rule. The catalogue is `docs/reference/event-identifiers.md`.

## 2. Define State Model

The aggregate state is an immutable Pydantic model representing reconstituted aggregate state:

```python
from uuid import UUID
from pydantic import BaseModel, Field

class CharacterInventoryState(BaseModel):
    character_id: UUID
    items: dict[str, int] = Field(default_factory=dict)
```

## 3. Implement DeclarativeAggregate

Subclass `DeclarativeAggregate[StateModel]` and annotate state mutation methods with `@handles(EventType)`:

```python
from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles

class CharacterInventoryAggregate(DeclarativeAggregate[CharacterInventoryState]):
    aggregate_type = "CharacterSheet"
    requires_creation_event = True

    def acquire_item(self, item_id: str, item_name: str, quantity: int = 1) -> None:
        """Command method emitting the domain event."""
        self.create_event(
            LootItemAcquired,
            session_id=None,
            item_id=item_id,
            item_name=item_name,
            quantity=quantity,
        )

    @handles(LootItemAcquired)
    def _on_loot_acquired(self, event: LootItemAcquired) -> None:
        """Pure event handler updating internal state."""
        items = dict(self.state.items)
        items[event.item_id] = items.get(event.item_id, 0) + event.quantity
        self._state = self.state.model_copy(update={"items": items})
```

## 4. Save and Reconstitute via AggregateRepository

```python
from runefoble_platform.event_sourcing import create_aggregate_repository

# Initialize repository. It resolves the process event store on every operation.
repo = create_aggregate_repository(CharacterInventoryAggregate)

# Create and mutate
char_id = uuid4()
inv = CharacterInventoryAggregate(char_id)
inv.acquire_item(item_id="potion-heal", item_name="Healing Potion", quantity=2)
await repo.save(inv)

# Reload from event history
reloaded = await repo.load(char_id)
assert reloaded.state.items["potion-heal"] == 2
```

### Load without losing history

Use the helpers in `runefoble_platform.aggregate_loading`. Do not wrap `repo.load` in
`except Exception`.

- `load_or_create(repo, aggregate_id, factory)` returns the stored aggregate. It creates a new
  aggregate only when the stream does not exist (`AggregateNotFoundError`).
- `load_if_exists(repo, aggregate_id)` returns the stored aggregate, or `None` when the stream
  does not exist. Use it when the caller decides what an absent stream means.
- `load_or_404(repo, aggregate_id, detail)` returns the stored aggregate, or raises HTTP 404 with
  `detail` when the stream does not exist. Use it on routes that answer 404.
- Every other error reaches the caller. A store outage must never create an empty aggregate.
  A new empty stream with an existing id causes conflicting events on the next save.
- Routes never write their own `except AggregateNotFoundError`. Use these helpers instead.
- `save_or_conflict(repo, aggregate, conflict)` saves the aggregate. On an optimistic lock
  failure it raises the error that `conflict` returns. A route passes an `HTTPException` (409).
  A service passes its domain error. Use it for every save that can race.

Each service registers `register_store_unavailable_handlers(app)` in its `main.py`. The
handler maps `SQLAlchemyError` and `OSError` to HTTP 503 with no substitute data.

```python
from fastapi import HTTPException
from runefoble_platform.aggregate_loading import (
    load_if_exists,
    load_or_404,
    load_or_create,
    save_or_conflict,
)

agg = await load_or_create(repo, char_id, CharacterInventoryAggregate)  # write path
found = await load_if_exists(repo, char_id)  # service read: None means not found
char = await load_or_404(repo, char_id, "Character not found")  # route read: 404
await save_or_conflict(
    repo,
    agg,
    lambda: HTTPException(status_code=409, detail="The character changed. Retry."),
)
```

### Hold a repository at module level

Keep each repository behind a `LazyRepository` from `runefoble_platform.lazy_repository`. It
builds the repository on first use. `get` returns it. `set` replaces it, and `set(None)` resets
it. A test that needs another repository calls `set` and restores the previous value.

```python
from runefoble_platform.lazy_repository import LazyRepository

character_repository = LazyRepository(
    lambda: create_aggregate_repository(CharacterInventoryAggregate)
)
get_character_repository = character_repository.get
```

## 5. Testing with InMemoryEventStore

In pytest test fixtures, use `InMemoryEventStore()` for instant, zero-dependency unit tests. The root test configuration selects the memory backend with `RUNEFOBLE_EVENT_STORE_BACKEND=memory`. A deployed environment refuses that backend, so production code never selects it by default.

Repositories hold no store. Each one resolves the process store from the provider on every call, so a test replaces the store through `set_event_store`. The shared test harness (`tests/helpers/event_store_seam.py`) gives each test a fresh store and restores the previous one. Use `store_outage()` from the same module to make every store read fail for one block. Do not patch store classes.

```python
import pytest
from eventsource.adapters.memory.store import InMemoryEventStore
from eventsource.application.aggregates.repository import AggregateRepository

@pytest.mark.asyncio
async def test_inventory_aggregate():
    store = InMemoryEventStore()
    repo = AggregateRepository(event_store=store, aggregate_factory=CharacterInventoryAggregate)
    ...
```

To test a service route against a store, install the store through the provider seam instead of building a repository by hand:

```python
from tests.helpers.event_store_seam import store_outage

with store_outage():  # every read fails with a connection error
    res = client.get(f"/api/v1/characters/{char_id}")
assert res.status_code == 503
```

To check that a failed write saves nothing, pass `record_appends=True`. The block then yields a list with one entry for each `append` made inside it. To spy on appends without an outage, use `record_appends()` from the same module.

## 6. Persistent Event Store (PostgreSQL)

The event store backend defaults to `postgresql`. In staging and production deployments, Helm sets `RUNEFOBLE_EVENT_STORE_BACKEND=postgresql` for every service that owns aggregate state. The setting maps to `PlatformSettings.event_store_backend`. Durable persistence uses `PostgreSQLEventStore`:

```python
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import (
    build_event_store,
    create_aggregate_repository,
    set_event_store,
)

settings = PlatformSettings(
    database_url="postgresql+asyncpg://runefoble_user:secret@postgres:5432/runefoble",
    event_store_backend="postgresql",
    postgres_pool_size=10,
    postgres_max_overflow=20,
)

# Automatically configures connection pooling, validates TCP reachability,
# and lazily provisions the events schema upon first access.
set_event_store(build_event_store(settings))
repo = create_aggregate_repository(CharacterInventoryAggregate)
```

The process store is owned by `EventStoreProvider`. `get_event_store()` builds it from the environment on first use. `set_event_store()` replaces it. `build_event_store(settings)` builds a store without installing it.

If the backend is `postgresql` and the PostgreSQL host is offline or unreachable during startup, `build_event_store` (and `get_event_store` on first use) raises `EventStoreInitializationError`. The service process exits instead of running on `InMemoryEventStore`. Select `memory` only for in-memory test runs. A deployed environment raises `EventStoreInitializationError` for `memory`. Use `event_store_kind()` to report the store kind (`postgresql` or `memory`) in health endpoints.
