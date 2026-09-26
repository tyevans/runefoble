# TASK-0001: Redis Streams Event Bus Infrastructure and Helm Integration

## Description
Integrate Redis Streams as the asynchronous pub/sub backbone across microservices, connecting `services/the_watcher`, `services/board_state`, `services/game_session`, and `gateway/api`. Add Redis to the Helm umbrella chart and Kind cluster configuration.

## Governing Documents
- ADRs: ADR-0002, ADR-0006, ADR-0007, ADR-0010
- PRDs: PRD-0001
- User Stories: US-0010

## Definition of Done
1. `RedisStreamsEventBus` in `libs/runefoble_platform/src/runefoble_platform/redis_bus.py` handles event publishing (`XADD`), consumer group registration (`XGROUP CREATE`), and message consumption (`XREADGROUP`) with acknowledgments (`XACK`).
2. Unit tests and integration tests with mocked or live Redis stream verify roundtrip event delivery.
3. Helm chart in `deployments/helm/runefoble` includes Redis deployment and service definitions.
4. Python test suite and Ruff lint gates pass with zero errors.
