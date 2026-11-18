# How-To: Test Cross-Service Calls with Live Upstream Services

## Overview
Some services call other services over HTTP. The gateway MCP tools call `board_state` and `rules_compendium`. This guide shows how to test such a call through public frontdoors only (ADR-0014).

The pattern uses real HTTP servers on loopback ports. The code under test sends real requests. Nothing patches the HTTP client. The shared helper is `tests/helpers/live_services.py`.

Use this pattern when:
- A tool or router calls an owning service over HTTP.
- You need to prove a 503 or an unreachable upstream returns an error, not a substitute value.

Do not use this pattern for a call to an external network service, such as an LLM vendor. Use a fake server at the process boundary instead. Start it with `serve(...)` as well.

## The Helper API

| Helper | Use it to |
|---|---|
| `serve(app, lifespan="off")` | Run an ASGI app on a free loopback port. It yields the base URL. Pass `lifespan="on"` for a service that builds state at start-up. |
| `unavailable_app(status_code=503)` | Build a stand-in upstream that answers every route with the given status. |
| `closed_port_url()` | Return a base URL where nothing listens. Connections are refused. |

Import the helpers from the test package:

```python
from tests.helpers.live_services import closed_port_url, serve, unavailable_app
```

## Recipe 1: Run a Real Owning Service as the Upstream

Start the owning service's FastAPI app, then point the caller at its URL. Set up test data through the owning service's public HTTP routes. Do not write to its private state.

```python
from board_state.main import app as board_app


@pytest.fixture(scope="module", autouse=True)
def owning_services() -> Iterator[dict[str, str]]:
    with pytest.MonkeyPatch.context() as env, serve(board_app) as board_url:
        env.setenv("BOARD_STATE_URL", board_url)
        with httpx.Client(base_url=board_url) as http:
            created = http.post(
                "/api/v1/boards", json={"session_id": "camp1", "cols": 10, "rows": 10}
            )
            assert created.status_code == 200, created.text
        yield {"board": board_url}
```

Services that build state at start-up need `lifespan="on"`:

```python
with serve(compendium_app, lifespan="on") as compendium_url:
    ...
```

`pytest.MonkeyPatch.context()` is used here only to set environment variables. It does not replace code.

## Recipe 2: Set the Upstream URL Setting

The gateway MCP reads its upstream addresses from the environment:

| Environment variable | Owning service |
|---|---|
| `BOARD_STATE_URL` | `board_state` |
| `CHARACTER_SHEET_URL` | `character_sheet` |
| `RULES_COMPENDIUM_URL` | `rules_compendium` |

`ServiceClient` reads these settings when it is created. Each tool call creates a client. A test can therefore set the variable with `monkeypatch.setenv` inside the test body.

Some settings are read once, at import time, into a module constant. Setting the variable in a test does not change them. Section "Known gaps" lists them. Do not patch these constants from a test. Fix the code so that it reads the setting at call time.

## Recipe 3: Simulate a 503 from the Upstream

```python
@pytest.mark.asyncio
async def test_inspect_board_returns_error_when_board_service_returns_503(monkeypatch):
    with serve(unavailable_app(503)) as down_url:
        monkeypatch.setenv("BOARD_STATE_URL", down_url)
        result = await call_tool("inspect_tactical_board", {"session_id": "camp-503"})

    assert result.isError is True
    assert "503" in tool_text(result)
```

The caller must return an error. It must not return a success body or a canned value.

## Recipe 4: Simulate an Unreachable Upstream

```python
@pytest.mark.asyncio
async def test_inspect_board_returns_error_when_board_service_is_unreachable(monkeypatch):
    monkeypatch.setenv("BOARD_STATE_URL", closed_port_url())
    result = await call_tool("inspect_tactical_board", {"session_id": "camp-down"})

    assert result.isError is True
    assert "unreachable" in tool_text(result)
```

## Recipe 5: Test The Watcher Against a Real Inference Worker

The Watcher calls the inference worker over HTTP. Run the worker app with `serve`, then send requests to The Watcher app through `httpx.ASGITransport`.

```python
with serve(api.app) as worker_url:
    ...
```

Use `closed_port_url()` for the unreachable-worker case. This case must return HTTP 503, not a template reply.

## Recipe 6: Run game_session as the Upstream for Gateway Campaign Routes

The gateway API reads its upstream URLs once, when its lifespan starts (TASK-0580). Set the variable first, then enter the lifespan with `with TestClient(gateway_app)`. A client that skips the lifespan has no upstream registry, and a client left over from an earlier lifespan holds closed HTTP clients.

The shared fixture `game_session_upstream` in `tests/conftest.py` does the setup:

1. Serves `game_session` on a loopback port with fresh in-memory campaign state.
2. Sets `RUNEFOBLE_GAME_SESSION_URL` with `monkeypatch`.
3. Trusts the signing issuer in both services through `trusted_ws_issuer`.

```python
@pytest.fixture
def client(game_session_upstream) -> Iterator[TestClient]:
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


def test_owner_creates_and_lists_a_campaign(client, trusted_ws_issuer) -> None:
    headers = {"Authorization": f"Bearer {trusted_ws_issuer.mint('dm-evelyn')}"}
    created = client.post("/api/v1/campaigns", json={"title": "Tomb"}, headers=headers)
    assert created.status_code == 201
```

Do not use `signing_issuer` in these tests. It replaces the gateway verifier, so game_session rejects the token.

## Assertions

- Assert on the public response: status code, error flag, or emitted event.
- Assert that the fake success value does not appear in the response.
- Do not assert on internal call counts of a client.

## What Not To Do

- Do not monkeypatch the HTTP client class, such as `httpx.AsyncClient`.
- Do not monkeypatch a method of an internal client, such as `SpiceDBClient.check_permission`.
- Do not monkeypatch a module constant of the code under test to change its upstream URL.
- Do not write a local uvicorn or `ThreadingHTTPServer` helper. Use `serve` or `closed_port_url`.
- Do not seed the owning service's private state. Create data through its public routes.
- Do not catch the upstream error in the test and treat it as a pass.

## Known Gaps

These tests still stub an upstream with `monkeypatch` or `patch`. Each gap needs a code change before the test can use this pattern.

| Test | Stub | Reason it is not migrated |
|---|---|---|
| `tests/test_blackbox_print_forge.py::test_blackbox_print_forge_spicedb_authorization` | `monkeypatch.setattr(SpiceDBClient, "check_permission", ...)` | No SpiceDB test server runs in the test environment. Needs a live SpiceDB or a process-boundary fake. |
| `tests/test_inference_worker_failure_contract.py::test_watcher_speech_surfaces_worker_503` and `::test_watcher_speech_unreachable_worker_is_503_not_template` | `select_worker_engine(monkeypatch, url)` from `tests/helpers/watcher_engine.py` | The Watcher reads `RUNEFOBLE_WATCHER_ENGINE` and `RUNEFOBLE_INFERENCE_URL` on each request (`the_watcher/engine_selection.py`). The helper sets both through `monkeypatch`. |
| `tests/test_inference_worker_failure_contract.py::use_worker_backend` fixture and `tests/test_inference_worker.py::mock_api` fixture | `monkeypatch.setattr(api, "llm_client", ...)` | `llm_client` is built at import time (`inference_worker/api.py`). Needs a call-time or env-driven backend selection. |

Tests in `tests/test_blackbox_mcp_*.py`, `tests/test_blackbox_gateway_*.py`, and settlement tests contain no stub of this kind. Their `monkeypatch` use is limited to environment variables.

## Related
- [`validate-e2e-journeys-with-playwright-bdd.md`](validate-e2e-journeys-with-playwright-bdd.md): browser journeys.
- [`add-a-watcher-ai-tool.md`](add-a-watcher-ai-tool.md): adding a gateway tool that calls a service over HTTP.
- ADR-0014: BDD and frontdoor setup. ADR-0015: audit remediation decisions (no substitute values on upstream failure).
