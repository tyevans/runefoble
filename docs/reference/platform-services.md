# Reference: Platform Services Architecture

## Overview
Runefoble is designed around a Kubernetes-first microservices topology deployed locally via Helm and Kind. Core business logic across bounded contexts connects to a standardized set of platform infrastructure services.

---

## Service Directory

| Platform Service | Upstream Image | Internal Host & Port | Ingress Route | Governing ADR | Test Double or Local Fallback |
|---|---|---|---|---|---|
| **PostgreSQL** | `pgvector/pgvector:pg16` | `postgres:5432` | None (Internal) | ADR-0005, ADR-0011 | `InMemoryEventStore` (test only; used when `RUNEFOBLE_USE_POSTGRES_EVENT_STORE=false`) |
| **Redis Streams** | `redis:7.2-alpine` | `runefoble-redis:6379` | None (Internal) | ADR-0006 | None. Services fail start-up when Redis is unreachable. Tests use a Redis test double (`MockAsyncRedis`). |
| **SpiceDB (Zanzibar)** | `authzed/spicedb:v1.34.0` | `spicedb:50051` (gRPC), `8443` (HTTP) | None (Internal) | ADR-0001 | None in services. Tests swap the factory client for `MockSpiceDBClient`. |
| **Zitadel (OIDC/AuthN)** | `ghcr.io/zitadel/zitadel:v2.54.0` | `zitadel:8080` | `auth.localhost` (own host, root path) | ADR-0005 | `ZitadelAuthService` (PyJWKClient RS256 verification of signature, `iss`, `aud`, `exp`, `sub`; no bypass) |
| **Silo (S3 Storage)** | `minio/minio:RELEASE.2024-01-01...` | `silo:9000` (S3), `9001` (UI) | None (Proxy via Gateway) | ADR-0005 | `FakeSilo` HTTP transport (tests only, no production fallback) |
| **OpenTelemetry Collector** | `otel/opentelemetry-collector-contrib` | `otel-collector:4317` (gRPC), `4318` (HTTP) | None (Internal) | ADR-0005 | Null Tracer / No-op Span Processor |
| **Loki** | `grafana/loki:3.0.0` | `loki:3100` | None (Internal) | ADR-0005 | Standard Python logging stdout |
| **Grafana** | `grafana/grafana:11.0.0` | `grafana:3001` | None (Port-forward) | ADR-0005 | Local metrics console |
| **OpenPanel** | `openpanel/openpanel:latest` | `openpanel:3000` | `/analytics` | ADR-0005 | Mock Event Buffer |
| **Swagger UI** | `swaggerapi/swagger-ui:v5.17.14` | `swagger-ui:8080` | `/docs`, `/swagger-ui` | ADR-0005 | Service `/openapi.json` direct endpoints |
| **Mailpit (Mock SMTP & UI)** | `axllent/mailpit:v1.21.8` | `mailpit:1025` (SMTP), `8025` (HTTP) | `/mail`, `/mailpit` | ADR-0005 | In-Memory `MailpitClient` Buffer (local and test only) |
| **Inference Worker (LLM, internal)** | First-party `services/inference_worker` | `inference-worker:8100` (HTTP, Helm `inference-worker` Deployment and Service) | Service credential `RUNEFOBLE_SERVICE_CREDENTIAL`, header `X-Runefoble-Service-Credential` (ADR-0015 e) | ADR-0007 | Chart default `backend: mock` (`RUNEFOBLE_WORKER_BACKEND=mock`, explicit, labelled `source: mock`); no silent fallback |

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
  - `RUNEFOBLE_USE_POSTGRES_EVENT_STORE`: Boolean flag (`true` to enable persistent `PostgreSQLEventStore`, default `false`). The Helm chart sets `true` for every service that owns aggregate state.
  - `RUNEFOBLE_POSTGRES_POOL_SIZE`: Async connection pool size (default `5`).
  - `RUNEFOBLE_POSTGRES_MAX_OVERFLOW`: Async connection pool max overflow (default `10`).
  - `RUNEFOBLE_EVENT_STORE_TABLE_NAME`: Event store table name (default `runefoble_events`).
- **Fail-Fast Initialization**: If `RUNEFOBLE_USE_POSTGRES_EVENT_STORE=true` and the database host is unreachable, `get_event_store()` raises `EventStoreInitializationError`. The service process exits at start-up. It never runs on `InMemoryEventStore` in this case. `InMemoryEventStore` is used only when the flag is `false` (for example, in tests).
- **Store Kind Reporting**: Service `/healthz` endpoints report `event_store` as `postgresql` or `memory`, from `event_store_kind()`.
- **Consumer Status Reporting**: Services that run Redis Stream consumers (`campaign-analytics`, `soundscape`) report `consumers` on `/healthz`, one entry per consumer set, with `running` or `failed`. The endpoint returns `503` when any consumer is `failed`. See [Run Supervised Redis Stream Consumers](../how-to/run-supervised-redis-stream-consumers.md).

### 2. Redis Streams (Event Streaming & Consumer Groups)
- **Role**: High-throughput distributed event bus powering pub/sub across bounded contexts.
- **Topics**: `runefoble.events.session`, `runefoble.events.board`, `runefoble.events.character`, `runefoble.events.voice`.
- **Environment Variables**: `RUNEFOBLE_REDIS_URL`, `REDIS_URL`.
- **Reference Guide**: [Redis Streams Event Bus](redis-streams-event-bus.md).

### 3. SpiceDB (Fine-Grained Zanzibar Authorization)
- **Role**: Object-level access control enforcing who can view, run, mutate, or roll within campaigns, characters, and boards.
- **Datastore Migrations**: Uses `spicedb datastore migrate head` executed via initContainers in the deployment and Helm schema job before serving or writing schemas.
- **Schema**: `libs/runefoble_auth/schema/runefoble.zed`.
- **Shared Factory**: `runefoble_auth.factory.get_spicedb_client()` is the only constructor for services and the gateway. It caches one client built from `PlatformSettings`. It raises `ConfigurationError` when the preshared key is missing.
- **Fail-Closed Errors**: `check_permission` returns `False` only for a definitive `NO_PERMISSION`. Other failures raise a typed error from `runefoble_auth.errors`:
  - `AuthzUnavailableError`: gRPC `UNAVAILABLE` or `DEADLINE_EXCEEDED`, or a socket error. The gateway maps it to `503`.
  - `AuthzSchemaError`: gRPC `INVALID_ARGUMENT` or `FAILED_PRECONDITION`. The name (type, relation, or permission) is not in `runefoble.zed`.
  - `AuthzWriteError`: any other failed write, delete, or schema write.
  - `AuthzError`: the base class of all three.
- **Schema Names Only**: Callers pass names from `runefoble.zed`. The client sends them unchanged. For example, `game_master` is valid and `gm` is not.
- **Environment Variables**: `RUNEFOBLE_SPICEDB_ENDPOINT`, `RUNEFOBLE_SPICEDB_PRESHARED_KEY`. The preshared key is an operator secret with no default outside tests. A process that cannot read it exits at startup and names the variable. Helm reads it from the `runefoble-credentials` Secret, key `spicedb-preshared-key`, and passes it as `SPICEDB_GRPC_PRESHARED_KEY` to the SpiceDB server. See [Chart Credentials](#chart-credentials).
- **Direct gRPC Enforcement**: `SpiceDBClient` connects directly over gRPC without silent mock fallbacks; errors fail fast to prevent authorization drift. Offline unit tests explicitly instantiate `MockSpiceDBClient`. Exception: the sync service (`libs/runefoble_auth/src/runefoble_auth/sync.py`) accepts a `MockSpiceDBClient` through its constructor and reports `backend: mock` when it does.
- **How-To Guide**: [Define and Check SpiceDB Zanzibar Permissions](../how-to/define-spicedb-zanzibar-permissions.md).

### 4. Zitadel (OIDC Identity & JWT Authentication)
- **Role**: Single Sign-On (SSO), PKCE login flows, user profile management, RS256 token issuance, and JWKS public key discovery (`/.well-known/jwks.json`).
- **Database Connection**: Configured with PostgreSQL admin credentials and `ZITADEL_DATABASE_POSTGRES_*_SSL_MODE=disable` for local Kind environments.
- **Issuer Variables** (set by the chart on every service that verifies tokens):
  - `RUNEFOBLE_ZITADEL_ISSUER`: the browser-facing issuer, `http://auth.localhost` by default. It must equal the token `iss` claim. Zitadel writes this value, built from `zitadel.externalDomain`, `externalPort`, and `externalSecure`.
  - `RUNEFOBLE_ZITADEL_INTERNAL_URL`: the in-cluster Zitadel origin, `http://zitadel:8080`. Discovery and JWKS requests go here with `Host` set to the issuer host (`auth.localhost`). Zitadel refuses other hosts. The verifier reads `jwks_uri` from discovery and rebases it onto this origin. The `iss` check still uses `RUNEFOBLE_ZITADEL_ISSUER`.
  - `RUNEFOBLE_ZITADEL_AUDIENCE`: the expected `aud` claim. The chart reads it from the `project-id` key of the Secret `runefoble-zitadel-client`. The bootstrap Job writes that key. The App Shell requests the project audience scope, so `aud` holds the project ID. The Node service refuses to start without it.
- **Other Variables**: `RUNEFOBLE_ZITADEL_CLIENT_ID`. (`RUNEFOBLE_AUTH_DEV_MODE` was removed in TASK-0520.)
- **Browser Runtime Config**: the frontend serves `/runtime-config.json` (issuer, client ID, scopes, provider name). The chart renders the template from `frontend.runtimeConfig`. An init container sets `clientId` and the project audience scope from the Secret `runefoble-zitadel-client`. The file holds no secret.
- **Zitadel Bootstrap Job**: the Helm hook Job `zitadel-bootstrap` creates the project `runefoble` and the application `runefoble-web`. It writes the Secret `runefoble-zitadel-client` (keys `project-id`, `client-id`). It reads the Zitadel admin PAT from the Secret `zitadel.bootstrap.adminSecret` (key `pat`). See [Authenticate with Zitadel OIDC](../how-to/authenticate-with-zitadel-oidc.md#bootstrap-the-zitadel-project-and-application).
- **Gateway CORS**: `RUNEFOBLE_CORS_ORIGINS` is a comma-separated list of browser origins allowed to call the gateway with credentials. The default is `http://localhost:5173,http://127.0.0.1:5173`. The value `*` is refused at startup.
- **How-To Guide**: [Authenticate with Zitadel OIDC](../how-to/authenticate-with-zitadel-oidc.md).

### 5. Silo S3 (Object Storage)
- **Role**: S3-compatible media asset storage for character avatars, map images, audio chronicles, and rule compendiums.
- **Buckets**: `runefoble-assets`, `runefoble-recordings`.
- **Environment Variables**: `RUNEFOBLE_SILO_ENDPOINT`, `RUNEFOBLE_SILO_ACCESS_KEY`, `RUNEFOBLE_SILO_SECRET_KEY`, `RUNEFOBLE_SILO_BUCKET_ASSETS`.
- **Failure Behaviour**: Every write, read, and delete goes to Silo. A transport error or a non-2xx status raises `AssetStorageError`. Forge and gateway routes return `503 Service Unavailable`. No object is stored and no asset id is issued. Nothing is written to process memory.
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
- **Graceful Fallback**: `MailpitClient` has built-in `fallback_in_memory=True` storing emails in a local memory buffer for offline test execution when Mailpit is not running.
- **How-To Guide**: [Test Email Signups with Mailpit](../how-to/test-email-signups-with-mailpit.md).

---

## Chart Credentials

The chart stores every credential in one Kubernetes Secret and reads it with `secretKeyRef`. No container manifest holds a credential as a plain value.

| Secret key | Values path | Read by |
|---|---|---|
| `postgres-password` | `credentials.postgres.password` | Every service with a database URL, SpiceDB, OpenPanel, Zitadel, Postgres |
| `silo-access-key` | `credentials.silo.accessKey` | Silo, Soundscape, Asset Forge |
| `silo-secret-key` | `credentials.silo.secretKey` | Silo, Soundscape, Asset Forge |
| `spicedb-preshared-key` | `credentials.spicedb.presharedKey` | SpiceDB, schema job, all services that call SpiceDB |
| `zitadel-masterkey` | `credentials.zitadel.masterKey` | Zitadel |
| `zitadel-admin-password` | `credentials.zitadel.adminPassword` | Zitadel |
| `grafana-admin-password` | `credentials.grafana.adminPassword` | Grafana |
| `service-credential` | `credentials.serviceCredential` | `the-watcher`, `inference-worker`, `gateway-mcp`, `board-state`, `character-sheet`, `game-session`, `rules-compendium` (ADR-0015 e). Not `gateway-api`. |

- **Local (`global.environment: local`)**: The chart renders the Secret from the `credentials` values. Those values are dev-only defaults. They are public in the repository.
- **Other environments**: Set `credentials.existingSecret` to the name of a Secret that you manage. The chart renders no Secret. It fails `helm template` when `global.environment` is not `local` and `credentials.existingSecret` is empty.
- **Database URLs**: The URLs use the Kubernetes `$(POSTGRES_PASSWORD)` expansion. The password does not appear in the URL value.

## Cross-Service URLs (TASK-0624)

The chart sets each service-to-service URL. The URL uses the in-cluster service name and the port from `services.<name>.port`. The chart renders each key only on the containers listed below. Each service reads its URL from the environment. No code default uses `localhost`.

| Environment variable | Value in cluster | Rendered on | Read by |
|---|---|---|---|
| `RUNEFOBLE_WATCHER_URL` | `http://the-watcher:8001` | `game-session`, `voice-agent` | `game_session` (autopilot; required in deployed mode), `voice_agent` (default `http://the-watcher:8001`) |
| `RUNEFOBLE_VOICE_AGENT_URL` | `http://voice-agent:8005` | `game-session` | `game_session` voice client |
| `RUNEFOBLE_INFERENCE_URL` | `http://inference-worker:8100` | `the-watcher` (only when `services.inferenceWorker` is set) | `the_watcher` |
| `RUNEFOBLE_SERVICE_CREDENTIAL` | Secret reference `runefoble-credentials`, key `service-credential` (`credentials.serviceCredential` in values) | `the-watcher`, `inference-worker`, `gateway-mcp`, `board-state`, `character-sheet`, `game-session`, `rules-compendium` | The MCP gateway and The Watcher send it. Receivers check it (ADR-0015 e) and refuse to start without it. |
| `SOUNDSCAPE_SERVICE_URL` | `http://soundscape:8009` | `gateway-api` | Gateway soundscape proxy (default `http://soundscape:8009`) |
| `CAMPAIGN_LORE_URL` | `http://campaign-lore:8006` | `gateway-api` | Gateway hub views |
| `CAMPAIGN_ANALYTICS_URL` | `http://campaign-analytics:8011` | `gateway-api` | Gateway hub views |
| `CHARACTER_SHEET_URL` | `http://character-sheet:8003` | `gateway-api` | Gateway character sub-resources |

The chart defines these keys in one block in `deployments/helm/runefoble/templates/services.yaml`. To add a consumer, add its container name to that key's `consumers` list.

### Deployed Mode and Start-Up Failures (ADR-0015 4)

The chart sets `RUNEFOBLE_ENVIRONMENT` on every service from `global.environment`. A deployed environment is `staging` or `production`. In a deployed environment, a missing dependency stops the service at start-up. It never falls back to a substitute.

- **`game_session`** refuses to start when `RUNEFOBLE_ENVIRONMENT` is `staging` or `production` and `RUNEFOBLE_WATCHER_URL` is unset. In `development` and `local`, it starts without the URL.
- **Auto-pilot** (`POST /api/v1/sessions/{id}/turns/auto-pilot`) returns `503 Service Unavailable` when `RUNEFOBLE_WATCHER_URL` is unset, when The Watcher is unreachable, when The Watcher returns a status other than `200`, or when it returns an invalid body. No action is recorded and the turn does not advance. Auto-pilot never runs a local engine in place of The Watcher.
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
- **Event store**: The replay reads `RUNEFOBLE_USE_POSTGRES_EVENT_STORE` and `RUNEFOBLE_DATABASE_URL`. Start-up fails if PostgreSQL is configured and unreachable.
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
| faster-whisper model cache | PVC `voice-agent-model-cache` (`services.voiceAgent.modelCache.size`, default `1Gi`) | `/var/lib/runefoble/whisper` |

The chart sets `RUNEFOBLE_VOICE_STT_MODEL_SIZE` from `services.voiceAgent.sttModelSize` (default `tiny.en`), `RUNEFOBLE_VOICE_STT_MODEL_DIR` to the mount path, and `RUNEFOBLE_VOICE_STT_DOWNLOAD_ENABLED=false`. The pod does not download the model.

Pre-fetch the model for Kind with `make voice-model-cache`. The target downloads the model to `.cache/voice-models` on the host and copies it into the running voice-agent pod. Set `VOICE_MODEL_SIZE` to use another model.

The `voice-agent` container has a readiness probe on `GET /healthz`. The probe fails when `espeak-ng --version` fails, or when the cache holds no model. A failed probe removes the pod from the service endpoints. The gateway then returns `503`.

## Engine Port Adapters

The module `runefoble_platform.engine_ports` holds the parts that settings-selected engine ports share. See [Add a Settings-Selected Engine Port Adapter](../how-to/add-an-engine-port-adapter.md) for the pattern.

- **`build_adapter(setting, value, registry)`**: returns `registry[value]()`. `registry` maps allowed values to zero-argument factories. An unknown value raises `UnknownAdapterError` (a `ValueError`). The message names `setting` and every allowed value.
- **`EngineUnavailableError(error_code, engine, message, *, engine_field="engine")`**: raised by an adapter when its engine cannot produce a result. `body()` returns `{"error": error_code, <engine_field>: engine, "message": message}`.
- **`engine_unavailable_handler`**: FastAPI exception handler. It returns HTTP `503` with the body under `detail`. Register it with `app.add_exception_handler(EngineUnavailableError, engine_unavailable_handler)`.

Services that register the handler: `voice_agent`, `asset_forge`.
