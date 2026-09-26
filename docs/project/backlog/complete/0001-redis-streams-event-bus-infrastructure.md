# TASK-0001: Redis Streams Event Bus Infrastructure and Helm Integration

## Description
Integrate Redis Streams as the asynchronous pub/sub backbone across microservices, connecting `services/the_watcher`, `services/board_state`, `services/game_session`, and `gateway/api`. Add Redis to the Helm umbrella chart and Kind cluster configuration.

## Governing Documents
- ADRs: ADR-0002, ADR-0006, ADR-0007, ADR-0010
- PRDs: PRD-0001
- User Stories: US-0010

## Deliverables Completed
- [x] Refined `RedisStreamsEventBus` in `libs/runefoble_platform/src/runefoble_platform/redis_bus.py` supporting `DomainEvent`, `BaseRunefobleEvent`, `BaseModel`, and dictionary payloads with JSON serialization of UUIDs and datetimes.
- [x] Added `deserialize_event` helper to recover registered `DomainEvent` classes via `get_event_class_or_none`.
- [x] Added `runefoble-redis` Deployment and ClusterIP Service to Helm chart (`deployments/helm/runefoble/templates/redis.yaml`).
- [x] Configured `redis` in `deployments/helm/runefoble/values.yaml` and injected `REDIS_URL` pointing to `redis://runefoble-redis:6379/0` into microservices in `services.yaml`.
- [x] Added comprehensive unit tests in `tests/test_redis_streams.py` covering publishing, consumer groups, reads, acknowledgments, and deserialization.
- [x] Verified all tests pass via `uv run pytest` and verified `ruff check`, `ruff format`, and `helm lint`.
