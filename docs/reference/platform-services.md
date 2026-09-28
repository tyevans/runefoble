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
| **Zitadel (OIDC/AuthN)** | `ghcr.io/zitadel/zitadel:v2.54.0` | `zitadel:8080` | `/auth` | ADR-0005 | `ZitadelAuthService` (PyJWKClient RS256 token verification with dev bypass) |
| **Silo (S3 Storage)** | `minio/minio:RELEASE.2024-01-01...` | `silo:9000` (S3), `9001` (UI) | None (Proxy via Gateway) | ADR-0005 | In-Memory Object Store Mock |
| **OpenTelemetry Collector** | `otel/opentelemetry-collector-contrib` | `otel-collector:4317` (gRPC), `4318` (HTTP) | None (Internal) | ADR-0005 | Null Tracer / No-op Span Processor |
| **Loki** | `grafana/loki:3.0.0` | `loki:3100` | None (Internal) | ADR-0005 | Standard Python logging stdout |
| **Grafana** | `grafana/grafana:11.0.0` | `grafana:3001` | None (Port-forward) | ADR-0005 | Local metrics console |
| **OpenPanel** | `openpanel/openpanel:latest` | `openpanel:3000` | `/analytics` | ADR-0005 | Mock Event Buffer |
| **Swagger UI** | `swaggerapi/swagger-ui:v5.17.14` | `swagger-ui:8080` | `/docs`, `/swagger-ui` | ADR-0005 | Service `/openapi.json` direct endpoints |
| **Mailpit (Mock SMTP & UI)** | `axllent/mailpit:v1.21.8` | `mailpit:1025` (SMTP), `8025` (HTTP) | `/mail`, `/mailpit` | ADR-0005 | In-Memory `MailpitClient` Buffer |

---

## Service Specifications

### 1. PostgreSQL (Relational Datastore & Event Persistence)
- **Role**: Durable persistence for events (`eventsource-py`), projections, and downstream service databases.
- **Initialization**: ConfigMap `/docker-entrypoint-initdb.d/init-multidb.sh` automatically provisions dedicated application and platform databases upon container startup with permissions granted to the default user (`runefoble_user`).
- **Databases**:
  - `runefoble`: Primary application state and domain event tables (`events`, with `runefoble_events` alias/table configuration).
  - `zitadel`: Identity provider database schema.
  - `spicedb`: Zanzibar relationship tuple storage engine.
  - `openpanel`: Telemetry event tables.
- **Environment Variables**:
  - `RUNEFOBLE_DATABASE_URL`: Connection string (`postgresql+asyncpg://...` or standard `postgresql://...` auto-normalized to asyncpg).
  - `RUNEFOBLE_USE_POSTGRES_EVENT_STORE`: Boolean flag (`true` to enable persistent `PostgreSQLEventStore`, default `false`).
  - `RUNEFOBLE_POSTGRES_POOL_SIZE`: Async connection pool size (default `5`).
  - `RUNEFOBLE_POSTGRES_MAX_OVERFLOW`: Async connection pool max overflow (default `10`).
  - `RUNEFOBLE_EVENT_STORE_TABLE_NAME`: Event store table name (default `runefoble_events`).
- **Graceful Fallback**: If `RUNEFOBLE_USE_POSTGRES_EVENT_STORE=true` but the database host is unreachable, `get_event_store()` logs a warning and falls back to `InMemoryEventStore`.

### 2. Redis Streams (Event Streaming & Consumer Groups)
- **Role**: High-throughput distributed event bus powering pub/sub across bounded contexts.
- **Topics**: `runefoble.events.session`, `runefoble.events.board`, `runefoble.events.character`, `runefoble.events.voice`.
- **Environment Variables**: `RUNEFOBLE_REDIS_URL`, `REDIS_URL`.
- **Reference Guide**: [Redis Streams Event Bus](redis-streams-event-bus.md).

### 3. SpiceDB (Fine-Grained Zanzibar Authorization)
- **Role**: Object-level access control enforcing who can view, run, mutate, or roll within campaigns, characters, and boards.
- **Datastore Migrations**: Uses `spicedb datastore migrate head` executed via initContainers in the deployment and Helm schema job before serving or writing schemas.
- **Schema**: `libs/runefoble_auth/schema/runefoble.zed`.
- **Environment Variables**: `RUNEFOBLE_SPICEDB_ENDPOINT`, `RUNEFOBLE_SPICEDB_PRESHARED_KEY`.
- **How-To Guide**: [Define and Check SpiceDB Zanzibar Permissions](../how-to/define-spicedb-zanzibar-permissions.md).

### 4. Zitadel (OIDC Identity & JWT Authentication)
- **Role**: Single Sign-On (SSO), PKCE login flows, user profile management, RS256 token issuance, and JWKS public key discovery (`/.well-known/jwks.json`).
- **Database Connection**: Configured with PostgreSQL admin credentials and `ZITADEL_DATABASE_POSTGRES_*_SSL_MODE=disable` for local Kind environments.
- **Environment Variables**: `RUNEFOBLE_ZITADEL_ISSUER`, `RUNEFOBLE_ZITADEL_CLIENT_ID`, `RUNEFOBLE_ZITADEL_JWKS_URL`, `RUNEFOBLE_AUTH_DEV_MODE`.
- **How-To Guide**: [Authenticate with Zitadel OIDC](../how-to/authenticate-with-zitadel-oidc.md).

### 5. Silo S3 (Object Storage)
- **Role**: S3-compatible media asset storage for character avatars, map images, audio chronicles, and rule compendiums.
- **Buckets**: `runefoble-assets`, `runefoble-recordings`.
- **Environment Variables**: `RUNEFOBLE_SILO_ENDPOINT`, `RUNEFOBLE_SILO_ACCESS_KEY`, `RUNEFOBLE_SILO_SECRET_KEY`, `RUNEFOBLE_SILO_BUCKET_ASSETS`.

### 6. Observability (OpenTelemetry, Loki, Grafana)
- **Role**: Unified distributed tracing, structured log aggregation, and real-time operational metrics.
- **Environment Variables**: `RUNEFOBLE_OTEL_ENABLED`, `RUNEFOBLE_OTEL_EXPORTER_OTLP_ENDPOINT`, `RUNEFOBLE_LOKI_ENDPOINT`.
- **How-To Guide**: [Instrument Services with OpenTelemetry](../how-to/instrument-services-with-opentelemetry.md).


### 7. OpenPanel (Privacy-Preserving Analytics)
- **Role**: Event tracking and funnels measuring session starts, turn times, and stand-in AI activation rates.
- **Environment Variables**: `RUNEFOBLE_OPENPANEL_ENDPOINT`, `RUNEFOBLE_OPENPANEL_CLIENT_ID`.
- **How-To Guide**: [Track Analytics Events](../how-to/track-analytics-events.md).

### 8. Mailpit (Mock SMTP Server & Email Testing UI)
- **Role**: Captures developer and test emails locally without outbound email delivery. Powers user email signups, Zitadel OIDC account confirmation, OTP verification codes, and password reset flows.
- **Web UI & REST API**: Accessible via Traefik Ingress at `/mail/` and `/mailpit/` (port 8025 internally).
- **SMTP Server**: Listens on port 1025 internally for RFC-822 email transmission.
- **Zitadel Integration**: Zitadel is configured via `ZITADEL_DEFAULTINSTANCE_SMTPCONFIGURATION_SMTP_HOST=mailpit:1025` to route all account verification emails directly into Mailpit.
- **Environment Variables**: `RUNEFOBLE_MAILPIT_SMTP_HOST`, `RUNEFOBLE_MAILPIT_SMTP_PORT`, `RUNEFOBLE_MAILPIT_HTTP_URL`, `RUNEFOBLE_MAILPIT_ENABLED`.
- **Graceful Fallback**: `MailpitClient` has built-in `fallback_in_memory=True` storing emails in a local memory buffer for offline test execution when Mailpit is not running.
- **How-To Guide**: [Test Email Signups with Mailpit](../how-to/test-email-signups-with-mailpit.md).

