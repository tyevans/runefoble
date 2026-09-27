# How-To: Decompose Microservice Routers

## Overview
As bounded context microservices evolve and accumulate capabilities, monolithic entrypoints (`main.py`) risk exceeding Hard Invariant 6 (file length limit < 500 lines). This guide provides the standard pattern for decomposing FastAPI microservices into modular `APIRouter` packages while preserving public API contracts, backward compatibility, and test frontdoors.

---

## Architecture Pattern

A modular microservice bounded context (or unified API Gateway) is organized into:
1. `routers/`: Distinct, single-responsibility `APIRouter` modules grouped by domain capability (e.g. `campaigns.py`, `spectator.py`, `health.py`).
2. `dependencies.py`: Shared runtime state, event bus instances, aggregate repositories, and clients.
3. `models.py`: Pydantic request and response schemas.
4. `main.py`: Thin orchestration shell (< 100 lines) instantiating FastAPI, mounting routers, exposing `/healthz` and `/ui/manifest`, and re-exporting core symbols.

This pattern is established across the `the_watcher`, `game_session`, `board_state`, `character_sheet`, and `voice_agent` bounded contexts as well as `gateway_api`.

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
import contextlib
from runefoble_platform.config import PlatformSettings
from runefoble_platform.redis_bus import RedisStreamsEventBus

platform_settings = PlatformSettings()
_event_bus: RedisStreamsEventBus | None = None


def get_event_bus() -> RedisStreamsEventBus | None:
    global _event_bus
    if _event_bus is None and platform_settings.redis_url:
        with contextlib.suppress(Exception):
            _event_bus = RedisStreamsEventBus(redis_url=platform_settings.redis_url)
    return _event_bus


def set_event_bus(bus: RedisStreamsEventBus | None) -> None:
    global _event_bus
    _event_bus = bus
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

When a single router accumulates multiple distinct sub-domains or exceeds ~250 lines (e.g. `copilot.py` splitting into `actions.py` and `whispers.py`, `intent.py` splitting into `disambiguation.py`, `compound.py`, and `speech.py`, or `caravan_contracts.py` splitting into `auth.py`, `board.py`, and `lifecycle.py`), promote it to a sub-router package:

```
routers/
├── __init__.py
├── capability_a.py
├── caravan_contracts/
│   ├── __init__.py      # Re-exports combined router and sub-routers
│   ├── auth.py          # Authorization and validation helpers
│   ├── board.py         # Notice board posting and querying endpoints
│   └── lifecycle.py     # Caravan claim, dispatch, ambush, and fulfillment
├── copilot/
│   ├── __init__.py      # Re-exports combined router and sub-routers
│   ├── actions.py       # Action interceptor and pause window endpoints
│   └── whispers.py      # Private narrative whisper endpoints
└── intent/
    ├── __init__.py      # Re-exports combined intent router and sub-routers
    ├── disambiguation.py# Ambiguity detection, clarification prompts, and target matching
    ├── compound.py      # Compound action combo parsing and rollback handling
    └── speech.py        # Single speech-to-intent parsing and event dispatch
```

The package `__init__.py` mounts each sub-router on a master router to preserve 100% backward compatibility for callers importing `copilot_router`:

```python
from fastapi import APIRouter
from <service>.routers.copilot.actions import router as actions_router
from <service>.routers.copilot.whispers import router as whispers_router

router = APIRouter()
router.include_router(actions_router)
router.include_router(whispers_router)

__all__ = ["actions_router", "router", "whispers_router"]
```

Alternatively, when decomposing a router module into companion HTTP and WebSocket modules without promoting to a subdirectory (e.g., `board_state/routers/previews.py` decomposed into `previews_http.py` and `previews_ws.py`), maintain the original module as a router aggregator facade:

```python
from fastapi import APIRouter
from board_state.routers.previews_http import (
    preview_move,
    preview_token_move,
    router as previews_http_router,
)
from board_state.routers.previews_ws import (
    board_websocket,
    router as previews_ws_router,
)

router = APIRouter(tags=["previews"])
router.include_router(previews_http_router)
router.include_router(previews_ws_router)

__all__ = [
    "board_websocket",
    "preview_move",
    "preview_token_move",
    "previews_http_router",
    "previews_ws_router",
    "router",
]
```



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

### 4. Preserve Backwards Compatibility
Ensure all existing functions and objects previously imported from `main.py` (such as `get_event_bus`, `set_event_bus`, or legacy route modules) are re-exported in `main.py` and `__all__`.

### 5. Verify Blackbox Frontdoors and File Limits
1. Ensure all existing integration tests run green.
2. Author blackbox tests exercising public HTTP endpoints through `fastapi.testclient.TestClient`.
3. Assert that all source files remain strictly under 500 lines:
   ```bash
   uv run pytest
   uv run ruff check .
   uv run ruff format --check .
   ```
