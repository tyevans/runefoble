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

This pattern is established across the `the_watcher`, `game_session`, and `board_state` bounded contexts as well as `gateway_api`.

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
