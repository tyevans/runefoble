# How-To: Define Event-Sourced Aggregates with eventsource-py

This guide explains how to define new domain events, state models, and `DeclarativeAggregate` classes in Runefoble using the `eventsource-py` library.

## 1. Define Domain Events

All domain events inherit from `BaseRunefobleEvent` and are registered with the `@register_event` decorator:

```python
from uuid import UUID
from eventsource.domain.event_registry import register_event
from runefoble_events.events import BaseRunefobleEvent


@register_event
class LootItemAcquired(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    item_id: str
    item_name: str
    quantity: int = 1
    rarity: str = "common"
```

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
from runefoble_platform.event_sourcing import (
    create_aggregate_repository,
    get_event_store,
)

# Initialize repository
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

## 5. Testing with InMemoryEventStore

In pytest test fixtures, use `InMemoryEventStore()` for instant, zero-dependency unit tests:

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

## 6. Persistent Event Store (PostgreSQL)

In staging and production deployments, durable event persistence is enabled via `PlatformSettings` and `PostgreSQLEventStore`:

```python
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import get_event_store, create_aggregate_repository

settings = PlatformSettings(
    database_url="postgresql+asyncpg://runefoble_user:secret@postgres:5432/runefoble",
    use_postgres_event_store=True,
    postgres_pool_size=10,
    postgres_max_overflow=20,
)

# Automatically configures connection pooling, validates TCP reachability,
# and lazily provisions the events schema upon first access.
store = get_event_store(settings=settings)
repo = create_aggregate_repository(CharacterInventoryAggregate, event_store=store)
```

If the PostgreSQL host is offline or unreachable during startup, `get_event_store` gracefully falls back to `InMemoryEventStore`, logging a diagnostic warning without terminating application boot.

## 7. Modular Aggregate Decomposition

To satisfy Hard Invariant 6 (< 500 lines per file) and separate concerns as domain rules grow, event-sourced bounded contexts are decomposed into three focused submodules:

1. **`rules.py`**: Static game balance rules, progression tables (e.g., `SPELL_SLOTS_TABLE`, `CLASS_HIT_DIE`), hazard damage formulas, and pure calculation functions (e.g., initiative tie-breaking, movement path costs).
2. **`models.py`**: Immutable Pydantic aggregate state schemas (`CharacterState`, `BoardState`, `GameSessionState`) equipped with transition helper methods (e.g., `with_health`, `with_token_moved`), alongside request/response DTOs.
3. **`aggregate.py`**: The `DeclarativeAggregate` implementation encapsulating command validation, domain event creation, and pure `@handles` projection methods delegating state updates to the models, while maintaining re-export compatibility.

