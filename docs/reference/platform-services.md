# Reference: Platform Services Architecture

## Overview
Runefoble is designed around a Kubernetes-first microservices topology deployed locally via Helm and Kind. Core business logic across bounded contexts connects to a standardized set of platform infrastructure services.

---

## Service Directory

| Platform Service | Upstream Image | Internal Host & Port | Ingress Route | Governing ADR | Local / Test Fallback |
|---|---|---|---|---|---|
| **PostgreSQL** | `postgres:16-alpine` | `postgres:5432` | None (Internal) | ADR-0005, ADR-0011 | `InMemoryEventStore` |
| **Redis Streams** | `redis:7.2-alpine` | `runefoble-redis:6379` | None (Internal) | ADR-0006 | `InMemoryEventBus` |
| **SpiceDB (Zanzibar)** | `authzed/spicedb:v1.34.0` | `spicedb:50051` (gRPC), `8443` (HTTP) | None (Internal) | ADR-0001 | `MockSpiceDBClient` (In-Memory) |
| **Zitadel (OIDC/AuthN)** | `ghcr.io/zitadel/zitadel:v2.54.0` | `zitadel:8080` | `/auth` | ADR-0005 | Stub `ZitadelAuthService` (`dev-user-001`) |
| **Silo (S3 Storage)** | `minio/minio:RELEASE.2024-01-01...` | `silo:9000` (S3), `9001` (UI) | None (Proxy via Gateway) | ADR-0005 | In-Memory Object Store Mock |
| **OpenTelemetry Collector** | `otel/opentelemetry-collector-contrib` | `otel-collector:4317` (gRPC), `4318` (HTTP) | None (Internal) | ADR-0005 | Null Tracer / No-op Span Processor |
| **Loki** | `grafana/loki:3.0.0` | `loki:3100` | None (Internal) | ADR-0005 | Standard Python logging stdout |
| **Grafana** | `grafana/grafana:11.0.0` | `grafana:3001` | None (Port-forward) | ADR-0005 | Local metrics console |
| **OpenPanel** | `openpanel/openpanel:latest` | `openpanel:3000` | `/analytics` | ADR-0005 | Mock Event Buffer |
| **Swagger UI** | `swaggerapi/swagger-ui:v5.17.14` | `swagger-ui:8080` | `/docs`, `/swagger-ui` | ADR-0005 | Service `/openapi.json` direct endpoints |

---

## Service Specifications

### 1. PostgreSQL (Relational Datastore & Event Persistence)
- **Role**: Durable persistence for events (`eventsource-py`), projections, and downstream service databases.
- **Databases**:
  - `runefoble`: Primary application state and domain event tables (`runefoble_events`).
  - `zitadel`: Identity provider database schema.
  - `spicedb`: Zanzibar relationship tuple storage engine.
  - `openpanel`: Telemetry event tables.
- **Environment Variables**: `RUNEFOBLE_DATABASE_URL` (`postgresql+asyncpg://...`)

### 2. Redis Streams (Event Streaming & Consumer Groups)
- **Role**: High-throughput distributed event bus powering pub/sub across bounded contexts.
- **Topics**: `runefoble.events.session`, `runefoble.events.board`, `runefoble.events.character`, `runefoble.events.voice`.
- **Environment Variables**: `RUNEFOBLE_REDIS_URL`, `REDIS_URL`.
- **Reference Guide**: [Redis Streams Event Bus](redis-streams-event-bus.md).

### 3. SpiceDB (Fine-Grained Zanzibar Authorization)
- **Role**: Object-level access control enforcing who can view, run, mutate, or roll within campaigns, characters, and boards.
- **Schema**: `libs/runefoble_auth/schema/runefoble.zed`.
- **Environment Variables**: `RUNEFOBLE_SPICEDB_ENDPOINT`, `RUNEFOBLE_SPICEDB_PRESHARED_KEY`.
- **How-To Guide**: [Define and Check SpiceDB Zanzibar Permissions](../how-to/define-spicedb-zanzibar-permissions.md).

### 4. Zitadel (OIDC Identity & JWT Authentication)
- **Role**: Single Sign-On (SSO), PKCE login flows, user profile management, and JWT signing.
- **Environment Variables**: `RUNEFOBLE_ZITADEL_ISSUER`, `RUNEFOBLE_ZITADEL_CLIENT_ID`.
- **How-To Guide**: [Authenticate with Zitadel OIDC](../how-to/authenticate-with-zitadel-oidc.md).

### 5. Silo S3 (Object Storage)
- **Role**: S3-compatible media asset storage for character avatars, map images, audio chronicles, and rule compendiums.
- **Buckets**: `runefoble-assets`, `runefoble-recordings`.
- **Environment Variables**: `RUNEFOBLE_SILO_ENDPOINT`, `RUNEFOBLE_SILO_ACCESS_KEY`, `RUNEFOBLE_SILO_SECRET_KEY`, `RUNEFOBLE_SILO_BUCKET_ASSETS`.

### 6. Observability (OpenTelemetry, Loki, Grafana)
- **Role**: Unified distributed tracing, structured log aggregation, and real-time operational metrics.
- **Environment Variables**: `RUNEFOBLE_OTEL_EXPORTER_OTLP_ENDPOINT`, `RUNEFOBLE_LOKI_ENDPOINT`.
- **How-To Guide**: [Instrument Services with OpenTelemetry](../how-to/instrument-services-with-opentelemetry.md).

### 7. OpenPanel (Privacy-Preserving Analytics)
- **Role**: Event tracking and funnels measuring session starts, turn times, and stand-in AI activation rates.
- **Environment Variables**: `RUNEFOBLE_OPENPANEL_ENDPOINT`, `RUNEFOBLE_OPENPANEL_CLIENT_ID`.
- **How-To Guide**: [Track Analytics Events](../how-to/track-analytics-events.md).
