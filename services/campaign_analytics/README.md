# Campaign Analytics & Chronicle Archive Microservice

Bounded context microservice projecting combat telemetry, tactical damage heatmaps, party MVP turn statistics, and interactive campaign milestone timelines from distributed Redis Streams domain events into PostgreSQL.

## Governing ADRs
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0006: Redis Streams Distributed Event Bus
- ADR-0011: eventsource-py Core Event Sourcing

## Endpoints
- `GET /healthz` - Health check endpoint
- `GET /metrics` - Prometheus metrics
- `GET /openapi.json` - OpenAPI specification
- `GET /api/v1/analytics/campaigns/{id}/heatmap` - Spatial coordinate hit/damage densities
- `GET /api/v1/analytics/campaigns/{id}/mvp` - Per-encounter/campaign MVP awards and turn metrics
- `GET /api/v1/analytics/campaigns/{id}/timeline` - Chronological session recaps and combat milestones
