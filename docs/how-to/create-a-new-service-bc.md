# How-To: Create a New Service Bounded Context

## Overview
When adding a new domain capability (e.g., `loot_generator`, `music_engine`), encapsulate it as a service bounded context under `services/`.

## Procedure

### 1. Initialize the Service with UV
Run `uv init` from the repository root:
```bash
uv init --app services/<new_service_name> --name <new-service-name>
```

### 2. Add Platform Dependencies
Link the new service to shared libraries and dependencies:
```bash
uv add fastapi uvicorn pydantic --project services/<new_service_name>
```

### 3. Add to Root Workspace pyproject.toml
In `pyproject.toml`, add `<new-service-name>` to `dependencies` and `tool.uv.sources`:
```toml
dependencies = [
    # ...
    "<new-service-name>",
]

[tool.uv.sources]
<new-service-name> = { workspace = true }
```

### 4. Create the Service Entrypoint
Implement `services/<new_service_name>/src/<new_service_name>/main.py`:
```python
from fastapi import FastAPI

app = FastAPI(title="Runefoble - <New Service Name>", version="0.1.0")

@app.get("/healthz")
async def health_check():
    return {"status": "ok", "service": "<new_service_name>"}
```

### 5. Register with Swagger UI and Helm
In `deployments/helm/runefoble/values.yaml`:
1. Add an entry under `swaggerUI.urls` to expose its OpenAPI spec.
2. Add an entry under `services` to deploy its Kubernetes pod.

### 6. Verify with Tests
Run `uv sync` followed by `uv run pytest`.
