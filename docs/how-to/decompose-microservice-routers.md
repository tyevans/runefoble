# How-To: Decompose Microservice Routers

## Overview
As bounded context microservices evolve and accumulate capabilities, monolithic entrypoints (`main.py`) risk exceeding Hard Invariant 6 (file length limit < 500 lines). This guide provides the standard pattern for decomposing FastAPI microservices into modular `APIRouter` packages while preserving public API contracts and test frontdoors.

---

## Architecture Pattern

A modular microservice bounded context (or unified API Gateway) is organized into:
1. `routers/`: Distinct, single-responsibility `APIRouter` modules grouped by domain capability (e.g. `campaigns.py`, `spectator.py`, `health.py`).
2. `dependencies.py`: Shared runtime state, event bus instances, aggregate repositories, and clients.
3. `models.py`: Pydantic request and response schemas.
4. `main.py`: Thin orchestration shell (< 100 lines) instantiating FastAPI, mounting routers, exposing `/healthz` and `/ui/manifest`, and re-exporting core symbols.

This pattern is established across the `the_watcher`, `board_state`, `character_sheet`, and `voice_agent` bounded contexts as well as `gateway_api`.

`game_session` has no `dependencies.py`. It builds an app container at start-up and its routers read the container through `Depends` providers (ADR-0021 D6). See [Compose a Service with an App Container](compose-a-service-with-an-app-container.md). TASK-0859 moves the other services to the same pattern.

```
services/<service_name>/src/<service_name>/  (or gateway/api/src/gateway_api/)
├── __init__.py
├── main.py              # Thin orchestration shell (< 100 lines)
├── dependencies.py      # Runtime state, event bus, repository
├── models.py            # Domain request/response models
└── routers/
    ├── __init__.py      # Re-exports sub-routers
    ├── capability_a.py  # Focused APIRouter
    └── capability_b.py  # Focused APIRouter
```

---

## Step-by-Step Procedure

### 1. Extract Shared Dependencies and Runtime State
Create `services/<service>/src/<service>/dependencies.py` to hold aggregate repositories, event bus accessors, and configuration settings:

```python
from __future__ import annotations
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import EventBusProvider

platform_settings = PlatformSettings()
event_bus_provider = EventBusProvider(platform_settings)
get_event_bus = event_bus_provider.get
set_event_bus = event_bus_provider.set
```

### 2. Create Focused APIRouter Modules
Under `routers/`, create domain-specific router files. Each router should define its routes and use dependencies from `dependencies.py`:

```python
from fastapi import APIRouter
from <service>.dependencies import get_event_bus
from <service>.models import MyRequest, MyResponse

router = APIRouter(tags=["capability_a"])

@router.post("/api/v1/<service>/action", response_model=MyResponse)
async def perform_action(req: MyRequest) -> MyResponse:
    # Handle domain action and event publishing
    ...
```

Export all routers in `routers/__init__.py`:

```python
from <service>.routers.capability_a import router as capability_a_router
from <service>.routers.capability_b import router as capability_b_router

__all__ = ["capability_a_router", "capability_b_router"]
```

When a single router accumulates multiple distinct sub-domains or exceeds ~250 lines (e.g. `copilot.py` splitting into `actions.py` and `whispers.py`, `intent.py` splitting into `disambiguation.py`, `compound.py`, and `speech.py`, `caravan_contracts.py` splitting into `auth.py`, `board.py`, and `lifecycle.py`, or `codex.py` splitting into `schemas.py`, `entries.py`, and `referencing.py`), promote it to a sub-router package:

```
routers/
├── __init__.py
├── capability_a.py
├── caravan_contracts/
│   ├── __init__.py      # Re-exports combined router and sub-routers
│   ├── auth.py          # Authorization and validation helpers
│   ├── board.py         # Notice board posting and querying endpoints
│   └── lifecycle.py     # Caravan claim, dispatch, ambush, and fulfillment
├── codex/
│   ├── __init__.py      # Re-exports combined codex router and sub-routers
│   ├── entries.py       # REST endpoints for entry publishing, retrieval, update, filtering
│   ├── referencing.py   # Cross-referencing, entity link extraction, mention resolution
│   └── schemas.py       # Pydantic request/response schemas and entry formatting
├── auth/
│   ├── __init__.py      # Re-exports combined router mounted at /api/v1/auth
│   ├── admin.py         # Local dev admin seeding and invitation endpoints
│   ├── dev_mail.py      # Mailpit test emails, inbox listing, and health diagnostics
│   ├── registration.py  # User signup, OTP verification, and resend endpoints
│   ├── schemas.py       # Pydantic request/response schemas and request models
│   └── tokens.py        # OAuth2 token issuance, refresh, and logout
├── copilot/
│   ├── __init__.py      # Re-exports combined router and sub-routers
│   ├── actions.py       # Action interceptor and pause window endpoints
│   └── whispers.py      # Private narrative whisper endpoints
├── settlement/
│   ├── router.py         # Haven builder aggregator facade (< 40 lines)
│   ├── haven/
│   │   ├── __init__.py   # Re-exports haven routers, handlers, and loaders (< 60 lines)
│   │   ├── loaders.py    # Aggregate loading and Zanzibar authorization (< 130 lines)
│   │   ├── routes_havens.py # Haven founding, projection, and listing (< 130 lines)
│   │   ├── routes_establishments.py # District zoning and construction (< 130 lines)
│   │   └── routes_upgrades.py # Civic tier scaling and facility upgrades (< 130 lines)
│   ├── workers_router.py # Aggregator facade (< 35 lines)
│   └── workers/
│       ├── __init__.py   # Re-exports models and dynamic router properties
│       ├── loaders.py    # Aggregate loading and Zanzibar authorization (< 80 lines)
│       ├── operations.py # Assignment and operating cost recalculation (< 125 lines)
│       ├── routes_roster.py # Worker assignment and roster listing (< 120 lines)
│       ├── routes_relationships.py # Ties, mood updates, rumors (< 100 lines)
│       └── routes_inventory.py # Shelf inventory, item prices, restocking (< 90 lines)
└── intent/
    ├── __init__.py      # Re-exports combined intent router and sub-routers
    ├── disambiguation.py# Ambiguity detection, clarification prompts, and target matching
    ├── compound.py      # Compound action combo parsing and rollback handling
    └── speech.py        # Single speech-to-intent parsing and event dispatch
```

The package `__init__.py` mounts each sub-router on a master router. Defect (DoR 9): it keeps `copilot_router` importable for existing callers. Removal: TASK-0490:

```python
from fastapi import APIRouter
from <service>.routers.copilot.actions import router as actions_router
from <service>.routers.copilot.whispers import router as whispers_router

router = APIRouter()
router.include_router(actions_router)
router.include_router(whispers_router)

__all__ = ["actions_router", "router", "whispers_router"]
```

When a router module splits into companion HTTP and WebSocket modules, do not keep the original module as an aggregator facade. Mount each sub-router directly. For example, `services/board_state/src/board_state/routers/previews.py` was decomposed into `previews_http.py` and `previews_ws.py`. The facade was then retired (TASK-0492), and the package `__init__.py` and `main.py` mount both sub-routers:

```python
from board_state.routers.previews_http import router as previews_http_router
from board_state.routers.previews_ws import router as previews_ws_router

app.include_router(previews_http_router)
app.include_router(previews_ws_router)
```

Callers import each symbol from the module that defines it. Do not re-export it from a parent module.


### 3. Maintain Thin Orchestration Shell in main.py
Keep `main.py` concise and declarative:

```python
from fastapi import FastAPI
from <service>.dependencies import get_event_bus, set_event_bus
from <service>.routers import capability_a_router, capability_b_router

app = FastAPI(title="Runefoble - <Service Name>", version="0.1.0")

app.include_router(capability_a_router)
app.include_router(capability_b_router)

@app.get("/healthz")
async def health_check():
    return {"status": "ok", "service": "<service>"}

@app.get("/ui/manifest")
def get_ui_manifest():
    return {
        "service": "<service>",
        "package": "@runefoble/<service>-ui",
        "components": [],
        "version": "0.1.0",
    }
```

### 4. Update Call Sites (DoR 9)
Do not re-export symbols from `main.py`. Update every caller to the new module and delete the old import path.

### 5. Verify Blackbox Frontdoors and File Limits
1. Ensure all existing integration tests run green.
2. Author blackbox tests exercising public HTTP endpoints through `fastapi.testclient.TestClient`.
3. Assert that all source files remain strictly under 500 lines:
   ```bash
   uv run pytest
   uv run ruff check .
   uv run ruff format --check .
   ```
