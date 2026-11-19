# How to Import Universal VTT Maps and Register Dynamic MCP Tools

This guide explains how to import community battlemaps using the Universal VTT (`.dd2vtt`) standard and dynamically register custom runtime tools on the FastMCP gateway without restarting the server.

---

## Prerequisites

- Local development environment or running Kubernetes cluster (`make cluster-up` or local services)
- UV monorepo workspace installed
- Silo S3 object storage operational (or in-memory mock fallback)

---

## 1. Importing Universal VTT (`.dd2vtt`) Maps

Universal VTT maps created in tools such as Dungeondraft, Dungeon Alchemist, or Arkenforge export `.dd2vtt` JSON files containing grid metadata, line-of-sight wall vectors, door portals, ambient lights, and an embedded base64 background image.

### Uploading via HTTP Multipart Frontdoor

The board must exist before you import. Create it first with `POST /api/v1/boards`. Import and door or light routes return `404` for an unknown board. They never create one.

```bash
curl -X POST "http://localhost:8002/api/v1/boards" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "camp-01"}'
```

Then send a `POST` request with the `.dd2vtt` file:

```bash
curl -X POST "http://localhost:8002/api/v1/board/camp-01/import/uvtt" \
  -F "file=@cavern_lair.dd2vtt;type=application/json"
```

Or via Python `httpx` or `requests`:

```python
import httpx

with open("cavern_lair.dd2vtt", "rb") as f:
    response = httpx.post(
        "http://localhost:8002/api/v1/board/camp-01/import/uvtt",
        files={"file": ("cavern_lair.dd2vtt", f, "application/json")},
    )

data = response.json()
print(f"Imported map dimensions: {data['cols']}x{data['rows']}")
print(f"Extracted wall segments: {len(data['wall_segments'])}")
print(f"Background texture URL: {data['background_image_url']}")
```

### Ingestion Flow & Effects

When `.dd2vtt` data is ingested:
1. **Resolution & Dimensions**: Grid resolution (`pixels_per_grid`) and canvas dimensions (`cols`, `rows`) are extracted and set on `BoardState`.
2. **Line of Sight & Portals**: Vector paths from `line_of_sight` are decomposed into segment dictionaries `{"x1", "y1", "x2", "y2", "wall_type": "wall"}`.
3. **Interactive Doors & Secret Portals**: Doors are parsed into `DoorGeometry` structures containing coordinate segments `(x1, y1, x2, y2)`, pivot hinges `(pivot_x, pivot_y)`, status (`open`, `closed`, `locked`), secret flag, and detection DC (`dc_detection`).
4. **Dynamic Point Lights**: Ambient lights are mapped to `BoardLightModel` containing normalized color hex (`#ffffffff`), bright radius, dim radius, flicker intensity, and shadow flags.
5. **Obstacle Bounds**: Integer grid coordinates along wall segments are populated with `obstacle` tokens within bounds.
6. **Silo S3 Texture Storage**: Embedded base64 image data is decoded, validated for image MIME types, and uploaded to the `battlemaps/` bucket in Silo S3.
7. **Event Sourcing**: A `UniversalVTTImported` domain event is emitted and applied to the `BoardAggregate`.

### Interacting with Doors and Dynamic Lights

The `board_state` service provides dedicated REST and WebSocket frontdoors for door toggles and light manipulation:

These routes need an existing board. Create it with `POST /api/v1/boards` first.

```python
import httpx

# Toggle an interactive door
resp = httpx.post("http://localhost:8002/board/camp-01/doors/main_gate/toggle")
print("Door state:", resp.json()["door"]["status"])

# Query active doors on the tactical grid
doors = httpx.get("http://localhost:8002/board/camp-01/doors").json()["doors"]

# Place a dynamic point light source (e.g. torch or campfire)
httpx.post(
    "http://localhost:8002/board/camp-01/lights",
    json={
        "light_id": "torch_01",
        "x": 8.0,
        "y": 6.0,
        "color_hex": "#ffaa22",
        "bright_radius": 20.0,
        "dim_radius": 40.0,
        "flicker_intensity": 0.25,
    },
)
```

Real-time state changes emit `BoardDoorToggledEvent` and `BoardLightSourcePlacedEvent` CloudEvents, broadcasting mutations across party WebSockets with SpiceDB Zanzibar authorization enforcement.

---

## 2. Registering Dynamic FastMCP Tools at Runtime

The FastMCP Gateway (`gateway/mcp`) provides dynamic runtime tool registration, enabling creators and modders to supply custom action tools without redeploying or restarting the gateway.

### Registering a Tool via REST API

Post a `DynamicToolDefinition` to `/mcp/tools` on the MCP gateway (`http://gateway-mcp:8012` inside the cluster). The API gateway does not serve this route. The request needs a Zitadel bearer token. The gateway records the token subject as the tool's author. The body fields `author_id` and `user_id`, and the `X-User-Id` header, are ignored (TASK-0532).

The MCP gateway has no ingress path. It is reachable only inside the cluster (ADR-0001). To call it
from a developer machine, forward its port first. The examples below then use `localhost:8012`:

```bash
kubectl port-forward svc/gateway-mcp 8012:8012
```

```python
import httpx

auth = {"Authorization": f"Bearer {access_token}"}  # token of the modder who owns the tool

tool_spec = {
    "name": "calculate_spell_falloff",
    "description": "Calculates force damage falloff over tactical grid distance",
    "parameters": {
        "type": "object",
        "properties": {
            "base_damage": {"type": "integer", "description": "Base spell damage"},
            "distance": {"type": "integer", "description": "Hex or grid distance in units"},
        },
        "required": ["base_damage", "distance"],
    },
    "handler": {
        "effective_damage": {"$expr": "max(0, base_damage - max(0, distance * 2))"},
        "drop": {"$expr": "max(0, distance * 2)"},
    },
    "metadata": {"author": "Alex", "version": "1.0.0"},
}

response = httpx.post("http://localhost:8012/mcp/tools", json=tool_spec, headers=auth)
assert response.status_code == 200
print("Tool registered successfully:", response.json())
```

### Immediate FastMCP Discovery

Once registered, the tool is immediately visible to MCP clients. `session` is an initialized MCP `ClientSession` on the `/mcp` endpoint, with the caller bearer:

```python
# Discovered immediately without server restart
tools = {tool.name: tool for tool in (await session.list_tools()).tools}
assert "calculate_spell_falloff" in tools

# Executable directly by LLM agent action plans
result = await session.call_tool("calculate_spell_falloff", {"base_damage": 30, "distance": 5})
print(result.content[0].text)  # {"effective_damage": 20, "drop": 10}
```

### Declarative Handlers

A tool handler is data. The gateway never compiles or runs caller code (ADR-0020). The `handler` field is a non-empty JSON object. The tool returns this object after evaluation:

- `"${name}"` gives the argument `name` with its type kept. `"${who} hits for ${base}"` gives a string with the values inserted.
- `{"$expr": "max(0, base - dist * 2)"}` gives a number. Use numbers, parameter names, `+ - * / // %`, parentheses, and `max`, `min`, `abs`, `round`.
- `{"$dice": "2d6+3"}` gives the total of the dice plus the modifier. The limits are 100 dice and 1000 sides.
- An object or a list holds more of these values. Nesting is limited to 8 levels.

Registration refuses a handler with an unknown parameter name, an unknown `$` directive, a bad expression, or a limit breach. The response is HTTP 400 and no tool is added. A definition with no `handler`, or with the removed `handler_code` field only, returns HTTP 422. A runtime arithmetic error, such as division by zero, returns HTTP 400 at execution.

---

## 3. Updating and Deregistering Dynamic Tools

### Updating a Tool

Use `PUT /mcp/tools/{name}` to update parameters, description, or handler logic. The caller needs `manage` on the tool. The recorded author does not change:

```python
response = httpx.put(
    "http://localhost:8012/mcp/tools/calculate_spell_falloff",
    headers=auth,
    json={
        "name": "calculate_spell_falloff",
        "description": "Enhanced spell falloff calculation with elemental resistance",
        "parameters": {
            "type": "object",
            "properties": {
                "base_damage": {"type": "integer"},
                "distance": {"type": "integer"},
                "resistance": {"type": "number", "default": 0.0},
            },
            "required": ["base_damage", "distance"],
        },
        "handler": {
            "effective_damage": {
                "$expr": "max(0, base_damage - max(0, distance * 2)) * (1.0 - resistance)"
            },
        },
    },
)
```

### Deregistering a Tool

Use `DELETE /mcp/tools/{name}` to cleanly remove the tool from FastMCP discovery. The caller needs `manage`. The gateway revokes the author relation:

```python
response = httpx.delete("http://localhost:8012/mcp/tools/calculate_spell_falloff", headers=auth)
assert response.status_code == 200
```
