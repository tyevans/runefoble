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
| `serve_subprocess(app_path, env)` | Run an import path such as `game_session.main:app` in a child uvicorn process. The child reads its settings from `env`. It yields the base URL and stops when the block exits, also when the block raises. |
| `serve_subprocesses(apps, env)` | Run several import paths, such as `{"game_session": "game_session.main:app", "soundscape": "soundscape.main:app"}`, as child processes that share `env`. Each child gets its own free port. It yields a dict of base URLs. Every child stops when the block exits, also when a later child fails to start. |

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
        env.setenv("RUNEFOBLE_BOARD_STATE_URL", board_url)
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
| `RUNEFOBLE_BOARD_STATE_URL` | `board_state` |
| `RUNEFOBLE_CHARACTER_SHEET_URL` | `character_sheet` |
| `RUNEFOBLE_RULES_COMPENDIUM_URL` | `rules_compendium` |

`OwningServices` reads these settings on each tool call. The shared service client is reused per event loop, service, and base URL. A test can therefore set the variable with `monkeypatch.setenv` inside the test body, and a new base URL starts a new client.

Some settings are read once, at import time, into a module constant. Setting the variable in a test does not change them. Section "Known gaps" lists them. Do not patch these constants from a test. Fix the code so that it reads the setting at call time.

## Recipe 3: Simulate a 503 from the Upstream

```python
@pytest.mark.asyncio
async def test_inspect_board_returns_error_when_board_service_returns_503(monkeypatch):
    with serve(unavailable_app(503)) as down_url:
        monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", down_url)
        result = await call_tool("inspect_tactical_board", {"session_id": "camp-503"})

    assert result.isError is True
    assert "503" in tool_text(result)
```

The caller must return an error. It must not return a success body or a canned value.

## Recipe 4: Simulate an Unreachable Upstream

```python
@pytest.mark.asyncio
async def test_inspect_board_returns_error_when_board_service_is_unreachable(monkeypatch):
    monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", closed_port_url())
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

The shared fixture `game_session_upstream` in `tests/helpers/service_harness.py` does the setup:

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

## Recipe 6b: campaign_lore Debits game_session with the Caller's Bearer

`campaign_lore` moves stronghold gold through `game_session` (TASK-0795). The call forwards the caller's verified `Authorization` header and the service credential. `game_session` checks `stronghold.manage` for that user. Use the `game_session_upstream` fixture and the `lore_client` fixture in `tests/test_blackbox_west_marches_funding.py`. A refused connection is tested by setting `RUNEFOBLE_GAME_SESSION_URL` to `closed_port_url()` with `monkeypatch`. The expected answer is `503`, and the outpost store does not change.

## Recipe 7: Restart a Service Between Writes and Reads

A restart test proves that state lives in the event store, not in process memory. Do not
re-import service modules in the test process. Start each process with `serve_subprocess`.

1. Use the `restart_stack` fixture from `tests/helpers/restart_stack.py`. It starts a
   PostgreSQL event store, a Redis container, a live SpiceDB with `runefoble.zed`, and a fake
   Zitadel that serves the test JWKS over HTTP.
2. Seed SpiceDB relations with `restart_stack.grant([...])`.
3. Write through a public route in the first child. Leave the `with` block to stop it.
4. Start a second child with `restart_stack.start(app_path)` and read through a public route.

```python
with restart_stack.start("game_session.main:app") as base:
    posted = _post(f"{base}/api/v1/sessions/{session_id}/contracts/bounties", json=body, headers=h)
    assert posted.status_code == 201

with restart_stack.start("game_session.main:app") as base:
    listed = _get(f"{base}/api/v1/sessions/{session_id}/contracts/bounties", headers=h)
assert listed.status_code == 200
```

To prove a restart test detects in-process state, start the child with
`restart_stack.start(app_path, RUNEFOBLE_EVENT_STORE_BACKEND="memory")`. The second read must fail.

The restart tests run the services without a `docker` marker. They skip when Docker is absent,
as the soundscape and lore restart tests do. The `docker` marker is deselected by default.

## Assertions

- Assert on the public response: status code, error flag, or emitted event.
- Assert that the fake success value does not appear in the response.
- Do not assert on internal call counts of a client.

## Use the Shared Service Harness

`tests/helpers/service_harness.py` is the one place that sets service seams in tests. Its table `SERVICE_SEAMS` lists, for each service, the module that holds the SpiceDB client, the event bus and the bearer verifier.

These fixtures read the table. Every test gets the autouse fixtures. Each one sets a seam and restores the previous value.

| Fixture | Effect |
|---|---|
| `default_spicedb_client` (autouse) | Sets one strict `MockSpiceDBClient` in every service and in the shared factory. It does nothing for live SpiceDB tests. |
| `spicedb` | Returns that mock. Write tuples to it only to test SpiceDB itself. |
| `default_redis_event_bus` (autouse) | Sets one Redis Streams bus over the `mock_bus` double in every service. |
| `mock_bus` | Returns the Redis double behind that bus. Read published events from `mock_bus.streams`. |
| `default_service_verifiers`, `shared_issuer_in_session_verifiers` (autouse) | Trust the shared signing issuer in token-verifying services. |
| `trusted_ws_issuer` | Trusts the shared issuer in the gateway, game_session and the_watcher for one test. |
| `use_event_bus`, `use_redis_client` | Return a function. Call it with a bus or a Redis double to route every service publish there for one test, for example a failing Redis. The default fixture restores the seams. |
| `clean_soundscape_registries` (autouse) | Clears the soundscape session registries around each test. |
| `character_sheet_upstream`, `game_session_upstream` | Serve that service as a live loopback upstream. |

`tests/helpers/stream_events.py` has `assert_stream_events(mock_bus, *names, stream=...)`. It checks that a test published each named event. The default stream is the West Marches stream. Do not write a copy of it in a conftest.

To add a service seam, add one `ServiceSeams` row. Do not write a setter call in a conftest. A directory conftest only builds a `TestClient` and its own helpers.

The harness imports every module in `SERVICE_SEAMS` when pytest loads it. A misspelled module name stops the run at collection. No seam is skipped.

### Restore a Process Global

A test that sets a process global must put back the value it found. Do not set `None` at teardown. A getter that finds `None` builds a real client or store. A later test can then reach a real endpoint.

Use `tests/helpers/module_state.py` for any seam that is not in `SERVICE_SEAMS`:

| Name | Use |
|---|---|
| `seam_restorer` fixture | Request it in a fixture or test. Call `replace(get, set_, value)` to set a value, or `keep(get, set_)` to save the current value. Teardown restores each saved value, newest first. |
| `restored_seam(get, set_, value, replace=True)` | Context manager. Sets `value` inside the `with` block and restores the previous value on exit. |

```python
@pytest.fixture
def voice_coordinator(seam_restorer: SeamRestorer) -> VoiceRoomCoordinator:
    return seam_restorer.replace(
        get_voice_room_coordinator, set_voice_room_coordinator, VoiceRoomCoordinator()
    )
```

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
- [`test-user-flows-with-playwright-bdd.md`](test-user-flows-with-playwright-bdd.md): browser journeys.
- [`add-a-watcher-ai-tool.md`](add-a-watcher-ai-tool.md): adding a gateway tool that calls a service over HTTP.
- ADR-0014: BDD and frontdoor setup. ADR-0015: audit remediation decisions (no substitute values on upstream failure).
