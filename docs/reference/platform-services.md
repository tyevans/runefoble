# Reference: Platform Services Architecture

## Overview
Runefoble is designed around a Kubernetes-first microservices topology deployed locally via Helm and Kind. Core business logic across bounded contexts connects to a standardized set of platform infrastructure services.

---

## Service Directory

| Platform Service | Upstream Image | Internal Host & Port | Ingress Route | Governing ADR | Test Double or Local Fallback |
|---|---|---|---|---|---|
| **PostgreSQL** | `pgvector/pgvector:pg16` | `postgres:5432` | None (Internal) | ADR-0005, ADR-0011 | `InMemoryEventStore` (test only; selected by `RUNEFOBLE_EVENT_STORE_BACKEND=memory`; refused in `staging` and `production`) |
| **Redis Streams** | `redis:7.2-alpine` | `runefoble-redis:6379` | None (Internal) | ADR-0006 | None. Services fail start-up when Redis is unreachable. Tests use a Redis test double (`MockAsyncRedis`). |
| **SpiceDB (Zanzibar)** | `authzed/spicedb:v1.34.0` | `spicedb:50051` (gRPC), `8443` (HTTP) | None (Internal) | ADR-0001 | None in services. Tests swap the factory client for `MockSpiceDBClient`. |
| **Zitadel (OIDC/AuthN)** | `ghcr.io/zitadel/zitadel:v2.54.0` | `zitadel:8080` | `auth.localhost` (own host, root path) | ADR-0005 | `ZitadelAuthService` (PyJWKClient RS256 verification of signature, `iss`, `aud`, `exp`, `sub`; no bypass) |
| **Silo (S3 Storage)** | `cgr.dev/chainguard/minio@sha256:7618b82...` (MinIO build; `minio/minio` no longer publishes to Docker Hub) | `silo:9000` (S3), `9001` (UI) | None (Proxy via Gateway) | ADR-0005 | `FakeSilo` HTTP transport (tests only, no production fallback) |
| **OpenTelemetry Collector** | `otel/opentelemetry-collector-contrib` | `otel-collector:4317` (gRPC), `4318` (HTTP) | None (Internal) | ADR-0005 | Null Tracer / No-op Span Processor |
| **Loki** | `grafana/loki:3.0.0` | `loki:3100` | None (Internal) | ADR-0005 | Standard Python logging stdout |
| **Grafana** | `grafana/grafana:11.0.0` | `grafana:3001` | None (Port-forward) | ADR-0005 | Local metrics console |
| **OpenPanel** | `lindesvard/openpanel-dashboard:2.3.0` | `openpanel:3000` | `/analytics` | ADR-0005 | Mock Event Buffer |
| **Swagger UI** | `swaggerapi/swagger-ui:v5.17.14` | `swagger-ui:8080` | `/docs`, `/swagger-ui` | ADR-0005 | Service `/openapi.json` direct endpoints |
| **Mailpit (Mock SMTP & UI)** | `axllent/mailpit:v1.21.8` | `mailpit:1025` (SMTP), `8025` (HTTP) | `/mail`, `/mailpit` | ADR-0005 | None. An unreachable Mailpit raises `EmailTransportError` (HTTP 503) |
| **Inference Worker (LLM, internal)** | First-party `services/inference_worker` | `inference-worker:8100` (HTTP, Helm `inference-worker` Deployment and Service) | Service credential `RUNEFOBLE_SERVICE_CREDENTIAL`, header `X-Runefoble-Service-Credential` (ADR-0015 e) | ADR-0007 | Chart default `backend: openai_compatible` (`RUNEFOBLE_WORKER_BACKEND=openai_compatible`; `openaiCompatibleBaseUrl` must name a reachable endpoint). `mock` is refused. No silent fallback |

---

## Service Specifications

### 1. PostgreSQL (Relational Datastore & Event Persistence)
- **Role**: Durable persistence for events (`eventsource-py`), projections, and downstream service databases.
- **Initialization**: ConfigMap `/docker-entrypoint-initdb.d/init-multidb.sh` automatically provisions dedicated application and platform databases upon container startup with permissions granted to the default user (`runefoble_user`).
- **Storage**: The Helm chart runs PostgreSQL as a StatefulSet named `postgres`. Its data claim `data` mounts at `/var/lib/postgresql/data`. The data directory is `pgdata` inside the claim (`PGDATA`). Size and storage class come from `postgres.persistence.size` (default `5Gi`) and `postgres.persistence.storageClass` (default empty, which uses the cluster default). The init script runs only on an empty data directory. A pod restart keeps every database. Deleting the claim deletes the data.
- **Databases**:
  - `runefoble`: Primary application state and domain event tables (`events`, with `runefoble_events` alias/table configuration).
  - `zitadel`: Identity provider database schema.
  - `spicedb`: Zanzibar relationship tuple storage engine.
  - `openpanel`: Telemetry event tables.
- **Environment Variables**:
  - `RUNEFOBLE_DATABASE_URL`: Connection string (`postgresql+asyncpg://...` or standard `postgresql://...` auto-normalized to asyncpg). The Node service `audience_studio` takes only the plain `postgresql://` form.
  - `RUNEFOBLE_EVENT_STORE_BACKEND`: `postgresql` (default) or `memory`. `postgresql` selects the persistent `PostgreSQLEventStore`. `memory` selects `InMemoryEventStore` for tests and explicit injection only. The Helm chart sets `postgresql` for every service that owns aggregate state. A service in `staging` or `production` refuses `memory`.
  - `RUNEFOBLE_POSTGRES_POOL_SIZE`: Async connection pool size (default `5`).
  - `RUNEFOBLE_POSTGRES_MAX_OVERFLOW`: Async connection pool max overflow (default `10`).
  - `RUNEFOBLE_EVENT_STORE_TABLE_NAME`: Event store table name (default `runefoble_events`).
- **Fail-Fast Initialization**: With the `postgresql` backend (the default) and an unreachable database host, `get_event_store()` raises `EventStoreInitializationError`. The service process exits at start-up. It never runs on `InMemoryEventStore` in this case.
- **Memory Backend**: `InMemoryEventStore` is used only when `RUNEFOBLE_EVENT_STORE_BACKEND=memory` is set explicitly. The root test configuration sets it. A deployed environment (`staging` or `production`) that selects `memory` raises `EventStoreInitializationError` at start-up. No setting falls back to memory.
- **Store Kind Reporting**: Service `/healthz` endpoints report `event_store` as `postgresql` or `memory`, from `event_store_kind()`.
- **Campaign Analytics Start-up Failure**: `campaign-analytics` requires PostgreSQL and Redis. If PostgreSQL is unreachable or its tables cannot be created, start-up raises `CampaignStoreStartupError`. If Redis is unreachable, start-up raises `EventBusUnavailableError`. The process exits and serves no requests. A non-PostgreSQL `RUNEFOBLE_DATABASE_URL` raises `StorageConfigurationError` when the app is built, before the lifespan starts. See [Project Campaign Analytics](../how-to/project-campaign-analytics-and-chronicle-timeline.md).
- **Consumer Status Reporting**: Services that run Redis Stream consumers (`campaign-analytics`, `soundscape`) report `consumers` on `/healthz`, one entry per consumer set, with `running` or `failed`. The endpoint returns `503` when any consumer is `failed`. See [Run Supervised Redis Stream Consumers](../how-to/run-supervised-redis-stream-consumers.md).
- **Gateway Downstream Status**: The gateway `/healthz` probes `the_watcher`, `game_session`, `board_state`, `character_sheet`, and `voice_agent` on each request. Each one reports `operational`, `degraded`, `unreachable`, or `not_configured`. The gateway stays `healthy` in every case. See [Ports and Endpoints](ports-and-endpoints.md#gateway-health-route-get-healthz).

### 2. Redis Streams (Event Streaming & Consumer Groups)
- **Role**: High-throughput distributed event bus powering pub/sub across bounded contexts.
- **Topics**: `runefoble.events.session`, `runefoble.events.board`, `runefoble.events.character`, `runefoble.events.voice`.
- **Environment Variables**: `RUNEFOBLE_REDIS_URL`. The chart renders it on every service only when `redis.enabled` is `true`. The value is `redis://runefoble-redis:<redis.port>/0`.
- **Storage**: The chart runs Redis as a StatefulSet named `runefoble-redis`. The append-only file is on the data claim `data` at `/data` (`--appendonly yes`). Stream entries and consumer group positions survive a pod restart. Size comes from `redis.persistence.size` (default `1Gi`). Decision: persist. Without the file, a restart drops every stream entry and every pending message that a consumer read but did not acknowledge. The domain record stays in PostgreSQL, but the stream projections (for example Campaign Analytics) would lose those messages.
- **Reference Guide**: [Redis Streams Event Bus](redis-streams-event-bus.md).

### 3. SpiceDB (Fine-Grained Zanzibar Authorization)
- **Role**: Object-level access control enforcing who can view, run, mutate, or roll within campaigns, characters, and boards.
- **Datastore Migrations**: Uses `spicedb datastore migrate head` executed via initContainers in the deployment and Helm schema job before serving or writing schemas.
- **Schema**: `libs/runefoble_auth/schema/runefoble.zed`.
- **Shared Factory**: `runefoble_auth.factory.get_spicedb_client()` is the only constructor for services and the gateway. It caches one client built from `runefoble_auth.settings.SpiceDBSettings`, not from `PlatformSettings`. It raises `ConfigurationError` when the preshared key is missing.
- **Test seam**: `runefoble_auth.factory.set_spicedb_client(client)` replaces the shared client. Pass `None` to build a fresh one. Tests restore the previous client with `tests/helpers/module_state.restored_seam`. No service exposes its own SpiceDB seam.
- **Fail-Closed Errors**: `check_permission` returns `False` only for a definitive `NO_PERMISSION`. Other failures raise a typed error from `runefoble_auth.errors`:
  - `AuthzUnavailableError`: gRPC `UNAVAILABLE` or `DEADLINE_EXCEEDED`, or a socket error. The gateway maps it to `503`.
  - `AuthzSchemaError`: gRPC `INVALID_ARGUMENT` or `FAILED_PRECONDITION`. The name (type, relation, or permission) is not in `runefoble.zed`.
  - `AuthzWriteError`: any other failed write, delete, or schema write.
  - `AuthzError`: the base class of all three.
- **Schema Names Only**: Callers pass names from `runefoble.zed`. The client sends them unchanged. For example, `game_master` is valid and `gm` is not.
- **Environment Variables**: `RUNEFOBLE_SPICEDB_ENDPOINT` (or `SPICEDB_ENDPOINT`), `RUNEFOBLE_SPICEDB_PRESHARED_KEY`. `SpiceDBSettings` reads them. The preshared key is an operator secret with no default outside tests. A service that checks permissions calls `load_spicedb_settings()` at startup. Without the key, it exits with `ConfigurationError` and names the variable. A process that never checks permissions and only builds `PlatformSettings` starts without the key. Helm reads it from the `runefoble-credentials` Secret, key `spicedb-preshared-key`, and passes it as `SPICEDB_GRPC_PRESHARED_KEY` to the SpiceDB server. See [Chart Credentials](#chart-credentials).
- **Direct gRPC Enforcement**: `SpiceDBClient` connects directly over gRPC without silent mock fallbacks; errors fail fast to prevent authorization drift. Offline unit tests explicitly instantiate `MockSpiceDBClient`. Exception: the sync service (`libs/runefoble_auth/src/runefoble_auth/sync.py`) accepts a `MockSpiceDBClient` through its constructor and reports `backend: mock` when it does.
- **How-To Guide**: [Define and Check SpiceDB Zanzibar Permissions](../how-to/define-spicedb-zanzibar-permissions.md).

### 4. Zitadel (OIDC Identity & JWT Authentication)
- **Role**: Single Sign-On (SSO), PKCE login flows, user profile management, RS256 token issuance, and JWKS public key discovery (`/.well-known/jwks.json`).
- **Database Connection**: Configured with PostgreSQL admin credentials and `ZITADEL_DATABASE_POSTGRES_*_SSL_MODE=disable` for local Kind environments.
- **Issuer Variables** (set by the chart on every service that verifies tokens):
  - `RUNEFOBLE_ZITADEL_ISSUER`: the browser-facing issuer. It must equal the token `iss` claim. The settings default is `http://localhost:8080` (`libs/runefoble_platform/src/runefoble_platform/config.py`). The chart sets `http://auth.localhost`, built from `zitadel.externalDomain`, `externalPort`, and `externalSecure` (`deployments/helm/runefoble/templates/_helpers.tpl`).
  - `RUNEFOBLE_ZITADEL_INTERNAL_URL`: the in-cluster Zitadel origin, `http://zitadel:8080`. Discovery and JWKS requests go here with `Host` set to the issuer host (`auth.localhost`). Zitadel refuses other hosts. The verifier reads `jwks_uri` from discovery and rebases it onto this origin. The `iss` check still uses `RUNEFOBLE_ZITADEL_ISSUER`.
  - `RUNEFOBLE_ZITADEL_AUDIENCE`: the expected `aud` claim. The chart reads it from the `project-id` key of the Secret `runefoble-zitadel-client`. The bootstrap Job writes that key. The App Shell requests the project audience scope, so `aud` holds the project ID. When the variable is empty, the settings use `RUNEFOBLE_ZITADEL_CLIENT_ID`. The audience setting also reads the unprefixed name `ZITADEL_AUDIENCE`. The Node service (`audience_studio`) refuses to start without the issuer or the audience.
- **Other Variables**: `RUNEFOBLE_ZITADEL_CLIENT_ID` (default `runefoble-api`). It is the audience fallback. The Helm chart does not set it. No setting turns off verification. `RUNEFOBLE_AUTH_DEV_MODE` was removed in TASK-0520.
- **Identity Contract**: the surface rules, public routes, error codes, and removed routes are in [Identity and Token Contract](identity-and-token-contract.md).
- **Browser Runtime Config**: the frontend serves `/runtime-config.json` (issuer, client ID, scopes, provider name). The chart renders the template from `frontend.runtimeConfig`. An init container sets `clientId` and the project audience scope from the Secret `runefoble-zitadel-client`. The file holds no secret.
- **Zitadel Bootstrap Job**: the Helm hook Job `zitadel-bootstrap` creates the project `runefoble` and the application `runefoble-web`. It writes the Secret `runefoble-zitadel-client` (keys `project-id`, `client-id`). It reads the Zitadel admin PAT from the Secret `zitadel.bootstrap.adminSecret` (key `pat`). The `pat-publisher` sidecar in the Zitadel pod writes that Secret from the file that Zitadel creates on its first start (`ZITADEL_FIRSTINSTANCE_PATPATH`). No manual step is needed. See [Authenticate with Zitadel OIDC](../how-to/authenticate-with-zitadel-oidc.md#bootstrap-the-zitadel-project-and-application).
- **Gateway CORS**: `RUNEFOBLE_CORS_ORIGINS` is a comma-separated list of browser origins allowed to call the gateway with credentials. The default is `http://localhost:5173,http://127.0.0.1:5173`. The value `*` is refused at startup.
- **How-To Guide**: [Authenticate with Zitadel OIDC](../how-to/authenticate-with-zitadel-oidc.md).

### 5. Silo S3 (Object Storage)
- **Role**: S3-compatible media asset storage for character avatars, map images, audio chronicles, and rule compendiums.
- **Buckets**: `runefoble-assets`, `runefoble-recordings`.
- **Storage**: The chart runs Silo as a StatefulSet named `silo`. Its data claim `data` mounts at `/data`, the server data path. Size and storage class come from `silo.persistence.size` (default `10Gi`) and `silo.persistence.storageClass` (default empty). A pod restart keeps every object. Deleting the claim deletes every object.
- **Environment Variables**: `RUNEFOBLE_SILO_ENDPOINT`, `RUNEFOBLE_SILO_ACCESS_KEY`, `RUNEFOBLE_SILO_SECRET_KEY`, `RUNEFOBLE_SILO_BUCKET_ASSETS`.
- **Bucket Job**: the Helm hook Job `silo-buckets` runs after install and upgrade. It creates every bucket in `silo.buckets` (default `runefoble-assets`, `runefoble-recordings`) with `mc mb --ignore-existing`, so an existing bucket is not an error. No manual step is needed. The image is `silo.bucketJob.image`, the Chainguard MinIO client, pinned by digest. The image has no shell. While Silo is not ready, the Job restarts its pod, up to `silo.bucketJob.backoffLimit` (default `10`). The Job reads the Silo keys from the credentials Secret and expands them into `MC_HOST_silo`, so the keys must be URL-safe. Asset Forge stores its objects in `runefoble-assets`.
- **Failure Behaviour**: Every write, read, and delete goes to Silo. A transport error or a non-2xx status raises `AssetStorageError`. Forge and gateway routes return `503 Service Unavailable`. The owning service logs the failure at error level with the bucket and the object key (`runefoble_platform.storage.log_storage_failure`). The log record never holds the object bytes or the Silo keys. No object is stored and no asset id is issued. Nothing is written to process memory.
- **Asset Index**: The metadata for each stored object is an event-sourced `AssetIndexAggregate` (`runefoble_platform.asset_index`). Its events are `AssetUploaded` and `AssetDeleted`. Its aggregate id is derived from the asset id. The index is written only after Silo confirms a write. It survives restarts and replicas when the event store is PostgreSQL.

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
- **No Fallback**: `MailpitClient` keeps no sent mail in memory. When the SMTP server or the Mailpit HTTP API is down, `send_email` and the read methods raise `EmailTransportError`. `check_health` reports the failure cause in `http_error` and `smtp_error`.
- **How-To Guide**: [Test Email Signups with Mailpit](../how-to/test-email-signups-with-mailpit.md).

---

## Chart Credentials

The chart stores every credential in one Kubernetes Secret and reads it with `secretKeyRef`. No container manifest holds a credential as a plain value.

| Secret key | Values path | Read by |
|---|---|---|
| `postgres-password` | `credentials.postgres.password` | Every service with a database URL, SpiceDB, OpenPanel, Zitadel, Postgres |
| `silo-access-key` | `credentials.silo.accessKey` | Silo, Silo bucket Job, Soundscape, Asset Forge |
| `silo-secret-key` | `credentials.silo.secretKey` | Silo, Silo bucket Job, Soundscape, Asset Forge |
| `spicedb-preshared-key` | `credentials.spicedb.presharedKey` | SpiceDB, schema job, all services that call SpiceDB |
| `zitadel-masterkey` | `credentials.zitadel.masterKey` | Zitadel |
| `zitadel-admin-password` | `credentials.zitadel.adminPassword` | Zitadel |
| `grafana-admin-password` | `credentials.grafana.adminPassword` | Grafana |
| `service-credential` | `credentials.serviceCredential` | `gateway-api`, `the-watcher`, `inference-worker`, `gateway-mcp`, `board-state`, `character-sheet`, `game-session`, `rules-compendium`, `campaign-lore` (ADR-0015 e). |

- **Local (`global.environment: local`)**: The chart renders the Secret from the `credentials` values. Those values are dev-only defaults. They are public in the repository.
- **Other environments**: Set `credentials.existingSecret` to the name of a Secret that you manage. The chart renders no Secret. It fails `helm template` when `global.environment` is not `local` and `credentials.existingSecret` is empty.
- **Database URLs**: The URLs use the Kubernetes `$(POSTGRES_PASSWORD)` expansion. The password does not appear in the URL value.

## Shared Platform Environment (TASK-0725)

The chart renders one platform environment for every service in the `services` map. The helper `runefoble.platformEnv` in `templates/_helpers.tpl` renders it. The helper uses the named templates `runefoble.databaseUrl`, `runefoble.redisUrl`, and `runefoble.plainEnv`. Each variable comes from `values.yaml`, not from a name in a template.

| Environment variable | Source | Rendered when |
|---|---|---|
| `POSTGRES_PASSWORD` | Secret `runefoble-credentials`, key `postgres-password` | Always |
| `RUNEFOBLE_SPICEDB_PRESHARED_KEY` | Secret, key `spicedb-preshared-key` | Always |
| `RUNEFOBLE_DATABASE_URL` | `postgres.username`, `postgres.port`, `postgres.database`, and the service `databaseDriver` (default `postgresql+asyncpg`) | Always |
| `RUNEFOBLE_SPICEDB_ENDPOINT` | `spicedb.grpcPort` | Always |
| `RUNEFOBLE_REDIS_URL` | `redis.port` | Only when `redis.enabled` is `true` |
| `RUNEFOBLE_OTEL_ENABLED` | `observability.enabled` | Always |
| `RUNEFOBLE_OTEL_EXPORTER_OTLP_ENDPOINT` | `observability.otelCollector.grpcPort` | Always |
| `RUNEFOBLE_ZITADEL_ISSUER`, `RUNEFOBLE_ZITADEL_INTERNAL_URL`, `RUNEFOBLE_ZITADEL_AUDIENCE` | Zitadel values and the bootstrap Secret | Always |

The helper sets these names for each container. The per-service keys in `services` set the other variables, for example `RUNEFOBLE_ENVIRONMENT`, `RUNEFOBLE_SILO_ENDPOINT`, `RUNEFOBLE_EVENT_STORE_BACKEND`, and the credentials. With `redis.enabled: false`, the chart sets no Redis URL. `PlatformSettings.redis_url` then uses its code default `redis://localhost:6379/0`, which does not reach a Redis in the cluster.

The database host is the Service `postgres`. The OTel host is the Service `otel-collector`. Both names are fixed in the helper. Change `postgres.port` or `observability.otelCollector.grpcPort` in `values.yaml`, and every URL follows it.

## Cross-Service URLs (TASK-0624)

`RUNEFOBLE_WATCHER_ENGINE` is not a URL. It selects The Watcher's engine adapters: `inference_worker` (default) or `heuristic`. The chart sets it on `the-watcher` through `services.theWatcher.env`. With `inference_worker`, The Watcher needs `RUNEFOBLE_INFERENCE_URL` and fails at start-up without it.

The chart sets each service-to-service URL. The URL uses the in-cluster service name and the port from `services.<name>.port`. The chart renders each key only on the containers listed below. Each service reads its URL from the environment. No code default uses `localhost`.

| Environment variable | Value in cluster | Rendered on | Read by |
|---|---|---|---|
| `RUNEFOBLE_WATCHER_URL` | `http://the-watcher:8001` | `game-session`, `voice-agent`, `gateway-api`, `gateway-mcp` | `game_session` (autopilot; required in deployed mode), `voice_agent` (transcript forwarding; no code default) |
| `RUNEFOBLE_VOICE_AGENT_URL` | `http://voice-agent:8005` | `game-session` | `game_session` voice client |
| `RUNEFOBLE_INFERENCE_URL` | `http://inference-worker:8100` | `the-watcher` (only when `services.inferenceWorker` is set) | `the_watcher` |
| `RUNEFOBLE_SERVICE_CREDENTIAL` | Secret reference `runefoble-credentials`, key `service-credential` (`credentials.serviceCredential` in values) | `gateway-api`, `the-watcher`, `inference-worker`, `gateway-mcp`, `board-state`, `character-sheet`, `game-session`, `rules-compendium`, `campaign-lore`, `voice-agent` | The gateway, MCP gateway, The Watcher, `game_session`, `campaign_lore`, and `voice_agent` (on each transcript forward to The Watcher, TASK-0732) send it. The receivers listed in the identity contract check it (ADR-0015 e). The chart sets it on every listed deployment. A receiver refuses to start without it. |
| `RUNEFOBLE_SOUNDSCAPE_URL` | `http://soundscape:8009` | `gateway-api` | Gateway soundscape proxy. No code default. |
| `RUNEFOBLE_GAME_SESSION_URL` | `http://game-session:8004` | `gateway-api`, `campaign-lore` | Gateway campaign routes. `campaign_lore` outpost funding debits the stronghold treasury (TASK-0795). |
| `RUNEFOBLE_CAMPAIGN_LORE_URL` | `http://campaign-lore:8006` | `gateway-api` | Gateway hub views |
| `RUNEFOBLE_CAMPAIGN_ANALYTICS_URL` | `http://campaign-analytics:8011` | `gateway-api` | Gateway hub views |
| `RUNEFOBLE_CHARACTER_SHEET_URL` | `http://character-sheet:8003` | `game-session`, `gateway-api`, `gateway-mcp` | Stand-in calls (`game_session`), gateway character routes, and MCP character tools. One name for all three processes. Unset means the process cannot reach `character_sheet` and fails with 503 or 502. |

The chart builds these keys from the `services` map in `deployments/helm/runefoble/values.yaml`. Each target sets `urlEnv` and `consumers`, and the helper `runefoble.serviceUrlEnv` in `templates/_services.tpl` renders them. To add a consumer, add its container name to the target's `consumers` list.

### Deployed Mode and Start-Up Failures (ADR-0015 4)

The chart sets `RUNEFOBLE_ENVIRONMENT` on every service from `global.environment`. A deployed environment is `staging` or `production`. In a deployed environment, a missing dependency stops the service at start-up. It never falls back to a substitute.

- **`game_session`** refuses to start when `RUNEFOBLE_ENVIRONMENT` is `staging` or `production` and `RUNEFOBLE_WATCHER_URL` is unset. In `development` and `local`, it starts without the URL.
- **Auto-pilot** (`POST /api/v1/sessions/{id}/turns/auto-pilot`) reads the absent character's stored stand-in policy from `character_sheet` (`RUNEFOBLE_CHARACTER_SHEET_URL`, service credential). It returns `503 Service Unavailable` when `RUNEFOBLE_WATCHER_URL` is unset, when `character_sheet` cannot supply the stored policy, when The Watcher is unreachable, when The Watcher returns a status other than `200`, or when it returns an invalid body. No action is recorded and the turn does not advance. Auto-pilot never runs a local engine in place of The Watcher.
- **Microfrontend manifests**: `character_sheet` and `soundscape` stop at start-up when `ui/manifest.json` is missing or is not a JSON object. `make build` runs `make check-ui-manifests`, which checks every `services/*/ui/manifest.json`.

---

## Campaign Lore Retrieval Backends

`LoreBackendSettings` (`libs/runefoble_platform`) selects each port of the Campaign Lore retrieval engine. The graph and passage ports are rebuilt from the event store at start-up.

- **`RUNEFOBLE_LORE_GRAPH`**: `projection` (default). Entity graph, rebuilt from `LoreDocument` events.
- **`RUNEFOBLE_LORE_VECTOR`**: `pgvector` (default, the only choice). Entity vectors in the `lore_entity_vectors` table on `RUNEFOBLE_DATABASE_URL`. The `memory` value is rejected.
- **`RUNEFOBLE_LORE_CHUNK`**: `memory` (default, the only choice). Passage corpus for BM25 and dense search, in process.
- **`RUNEFOBLE_LORE_EMBEDDING`**: `openai_compatible` (default, the only choice). The `fake` value is rejected. Requires the endpoint settings below.
- **`RUNEFOBLE_EMBEDDING_BASE_URL`**, **`RUNEFOBLE_EMBEDDING_MODEL`**, **`RUNEFOBLE_EMBEDDING_DIMENSION`**: Required. Start-up fails if one is missing or the endpoint does not answer.
- **`RUNEFOBLE_EMBEDDING_API_KEY`**, **`RUNEFOBLE_EMBEDDING_DOCUMENT_PREFIX`**, **`RUNEFOBLE_EMBEDDING_QUERY_PREFIX`**: Optional.
- **Event store**: The replay reads `RUNEFOBLE_EVENT_STORE_BACKEND` and `RUNEFOBLE_DATABASE_URL`. Start-up fails if PostgreSQL is the backend and unreachable.
- **Details**: [Embedding Providers](embedding-providers.md).

---

## Rules Compendium Retrieval Mode

`RulesCompendiumSettings` (`libs/runefoble_platform`) selects the retrieval mode of the Rules Compendium. The mode is reported in every search response as `retrieval_mode`.

- **`RUNEFOBLE_RULES_EMBEDDING`**: `lexical` (default). BM25 only. Responses report `lexical`.
- **`RUNEFOBLE_RULES_EMBEDDING`**: `openai_compatible`. BM25 fused with vector search. Responses report `hybrid`. Requires the endpoint settings below.
- **`RUNEFOBLE_EMBEDDING_BASE_URL`**, **`RUNEFOBLE_EMBEDDING_MODEL`**, **`RUNEFOBLE_EMBEDDING_DIMENSION`**: Required for `openai_compatible`. Start-up fails if one is missing.
- **`RUNEFOBLE_EMBEDDING_API_KEY`**, **`RUNEFOBLE_EMBEDDING_DOCUMENT_PREFIX`**, **`RUNEFOBLE_EMBEDDING_QUERY_PREFIX`**: Optional.
- **Details**: [Embedding Providers](embedding-providers.md).

---

## Wardrobe Image Generator

`WardrobeGeneratorSettings` (`libs/runefoble_platform`) selects the generator behind the `WardrobeGenerator` port. The Asset Forge service reads it at start-up.

- **`RUNEFOBLE_WARDROBE_GENERATOR`**: `placeholder` (default). Draws a flat colour portrait. It preserves no face and does not read the attire prompt. Any other value fails validation at start-up.

## Voice Agent Runtime Assets (TASK-0676)

The `voice-agent` image needs two runtime assets. The image and the Helm chart provide both. Nothing installs at pod start.

| Asset | Provided by | Location in pod |
|---|---|---|
| `espeak-ng` binary | Dockerfile build argument `SYSTEM_PACKAGES=espeak-ng` (`PYTHON_IMAGE_ROWS` in the Makefile) | `/usr/bin/espeak-ng` |
| faster-whisper model cache (`sttEngine: faster-whisper` only) | PVC `voice-agent-model-cache` (`services.voiceAgent.modelCache.size`, default `1Gi`) | `/var/lib/runefoble/whisper` |

The chart sets `RUNEFOBLE_VOICE_STT_MODEL_SIZE` (default `tiny.en`), `RUNEFOBLE_VOICE_STT_MODEL_DIR` (the mount path), and `RUNEFOBLE_VOICE_STT_DOWNLOAD_ENABLED=false` from `services.voiceAgent.env`. The pod does not download the model.

### Speech-to-Text Engine Values (TASK-0833)

`services.voiceAgent.sttEngine` sets `RUNEFOBLE_VOICE_STT_ENGINE`. `services.voiceAgent.sttBaseUrl` sets `RUNEFOBLE_VOICE_STT_BASE_URL`.

- `faster-whisper` (default): the model runs in the pod. The chart mounts the model cache.
- `whisper-cpp`: the pod calls a whisper.cpp HTTP server at `sttBaseUrl`, for example `http://<host>:8080`. The chart renders no model cache volume and no PVC. `sttBaseUrl` is required. Start-up fails without it.

Set both keys in `deployments/helm/runefoble/values.local.yaml`. The example file `values.local.example.yaml` shows them as comments.

Pre-fetch the model for Kind with `make voice-model-cache`. The target downloads the model to `.cache/voice-models` on the host and copies it into the running voice-agent pod. Set `VOICE_MODEL_SIZE` to use another model.

The `voice-agent` container has a readiness probe on `GET /healthz`. The probe fails when `espeak-ng --version` fails, or when the cache holds no model. A failed probe removes the pod from the service endpoints. The gateway then returns `503`.

## Engine Port Adapters

The module `runefoble_platform.engine_ports` holds the parts that settings-selected engine ports share. See [Add a Settings-Selected Engine Port Adapter](../how-to/add-an-engine-port-adapter.md) for the pattern.

- **`build_adapter(setting, value, registry)`**: returns `registry[value]()`. `registry` maps allowed values to zero-argument factories. An unknown value raises `UnknownAdapterError` (a `ValueError`). The message names `setting` and every allowed value.
- **`EngineUnavailableError(error_code, engine, message, *, engine_field="engine")`**: raised by an adapter when its engine cannot produce a result. `body()` returns `{"error": error_code, <engine_field>: engine, "message": message}`.
  It subclasses `ServiceUnavailableError` from `runefoble_platform.errors`, the one unavailable-error base.
- **`engine_unavailable_handler`**: FastAPI exception handler. It returns HTTP `503` with the body under `detail`. Register it with `app.add_exception_handler(EngineUnavailableError, engine_unavailable_handler)`.

Services that register the handler: `voice_agent`, `asset_forge`.
