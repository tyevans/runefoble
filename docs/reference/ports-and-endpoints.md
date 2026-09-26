# Reference: Ports and Endpoints

## Ingress Routes (localhost)

| Ingress Path | Destination Service | Description |
|---|---|---|
| `/` | `frontend:80` | Lit + Vite web application |
| `/api` | `gateway-api:8000` | REST and WebSocket API gateway |
| `/docs`, `/swagger-ui` | `swagger-ui:8080` | Unified Swagger UI aggregating all OpenAPI specs |
| `/auth` | `zitadel:8080` | Self-hosted Zitadel identity provider |

## Microservice Internal Ports

| Service | Internal Port | OpenAPI Path |
|---|---|---|
| `gateway-api` | `8000` | `/openapi.json` |
| `the-watcher` | `8001` | `/openapi.json` |
| `board-state` | `8002` | `/openapi.json` |
| `character-sheet` | `8003` | `/openapi.json` |
| `game-session` | `8004` | `/openapi.json` |
| `voice-agent` | `8005` | `/openapi.json` |

## Key Microservice Endpoints

| Service | Method | Route | Description |
|---|---|---|---|
| `the-watcher` | POST | `/api/v1/watcher/transcribe-and-act` | Parses spoken transcript, dispatches events to Redis Streams, triggers board actions |
| `the-watcher` | POST | `/api/v1/watcher/stand-in/act` | Generates autonomous action for absent player's character with penalties |
| `the-watcher` | POST | `/api/v1/watcher/stand-in/recap` | Generates humorous absentee session recap for returning players |
| `the-watcher` | POST | `/api/v1/watcher/narrate` | Generates atmospheric narration and DM rulings |
| `game-session` | POST | `/api/v1/sessions/{session_id}/turns/auto-pilot` | Executes automated stand-in turn for absent player, records action, dispatches events, and advances turn |
| `voice-agent` | POST | `/api/v1/voice/transcribe` | Transcribes player speech, emits `PlayerSpokeEvent` to Redis Streams, and forwards to The Watcher |
| `voice-agent` | POST | `/api/v1/voice/synthesize` | Generates TTS audio streams using persona voice models with filters |
| `voice-agent` | GET | `/api/v1/voice/personas` | Lists available voice persona models |
| `board-state` | GET | `/api/v1/boards/{session_id}` | Retrieves tactical grid dimensions and placed token states |
| `board-state` | POST | `/api/v1/boards/{session_id}/move` | Mutates token coordinates with spatial boundary enforcement |


## Infrastructure Ports

| Infrastructure | Service Name | Port | Description |
|---|---|---|---|
| PostgreSQL | `postgres` | `5432` | Relational database |
| Redis | `runefoble-redis` | `6379` | In-memory datastore and event streaming via Redis Streams |
| Silo (MinIO fork) | `silo` | `9000` (S3), `9001` (Console) | S3 Object Storage |
| SpiceDB | `spicedb` | `50051` (gRPC), `8443` (HTTP) | Zanzibar graph authorization |
| OpenPanel | `openpanel` | `3000` | Self-hosted analytics |
| Loki | `loki` | `3100` | Log aggregation |
| Grafana | `grafana` | `3001` | Metrics and observability dashboards |
| Storybook (Dev) | Local | `6006` | Component development studio |
