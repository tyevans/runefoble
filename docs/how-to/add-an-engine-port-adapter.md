# Add a Settings-Selected Engine Port Adapter

This guide shows how a service adds an engine port. The port is an interface in the owning service. A setting picks the adapter. An engine that cannot work returns an explicit `503`. It never returns substitute output.

Read this guide with ADR-0015 (decision 4, "Fallbacks hide failures"). A deployed service fails fast when a configured engine is missing. It does not switch to a fake.

## What Is Shared and What Is Not

The shared parts live in `libs/runefoble_platform/src/runefoble_platform/engine_ports.py`:

- `build_adapter` maps a setting value to a factory. An unknown value raises `UnknownAdapterError` and names the allowed values.
- `EngineUnavailableError` is the one error an adapter raises when its engine cannot produce a result.
- `engine_unavailable_handler` maps that error to HTTP `503`.

The parts that stay in each service:

- The port interface. Each port has its own methods and types. Do not merge ports into one interface.
- The settings class. Each service owns its environment prefix and its fields.
- The adapters. Each adapter wraps one engine.

Current engine ports:

| Service | Setting | Port | Adapters | Error code | Body key for the engine |
|---|---|---|---|---|---|
| `voice_agent` | `RUNEFOBLE_VOICE_STT_ENGINE` | `BaseTranscriber` | `faster-whisper`, `whisper-cpp` | `speech_engine_unavailable` | `engine` |
| `voice_agent` | `RUNEFOBLE_VOICE_TTS_ENGINE` | `BaseSynthesizer` | `espeak-ng` | `speech_synthesis_unavailable` | `engine` |
| `asset_forge` | `RUNEFOBLE_ASSET_FORGE_MAP_GENERATOR` | `MapGenerator` | `deterministic` | `map_generation_unavailable` | `generator` |
| `asset_forge` | `RUNEFOBLE_WARDROBE_GENERATOR` | `WardrobeGenerator` | `placeholder` | none (no failure path) | none |
| `rules_compendium` | `RUNEFOBLE_RULES_EMBEDDING` | `redstring.EmbeddingProvider` | `lexical`, `openai_compatible` | none (see Known Gaps) | none |
| `inference_worker` | `RUNEFOBLE_WORKER_BACKEND` | `LLMPort` | `openai_compatible`, `ollama` | `backend_unavailable` | `backend` (flat body, see Known Gaps) |
| `the_watcher` | `RUNEFOBLE_WATCHER_ENGINE` | `IntentParser`, `StandInDecider`, `SceneNarrator` (one setting selects all three) | `inference_worker`, `heuristic` | `backend_unavailable` | `backend` |

## Steps

### 1. Define the port in the owning service

Create a module in the service. Declare an abstract class. Document the error that it raises.

```python
class BaseTranscriber(ABC):
    engine_name: ClassVar[str]

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        """Raises EngineUnavailableError when the engine cannot produce a transcript."""
```

Set `engine_name` on each adapter. The name appears in the `503` body.

### 2. Add the setting

Add a field with a `Literal` type. The `Literal` lists the supported values. Pydantic rejects other values when the settings object is built.

```python
stt_engine: Literal["faster-whisper"] = "faster-whisper"
```

### 3. Register the adapters

Write one builder function in the service. Pass the registry to `build_adapter`. Each key is a setting value. Each value is a zero-argument factory. Only the factory for the configured value runs.

```python
from runefoble_platform.engine_ports import build_adapter


def build_transcriber(settings: VoiceAgentSettings) -> BaseTranscriber:
    return build_adapter(
        "RUNEFOBLE_VOICE_STT_ENGINE",
        settings.stt_engine,
        {
            "faster-whisper": lambda: FasterWhisperTranscriber(
                model_size=settings.stt_model_size,
            ),
        },
    )
```

The first argument is the environment variable name. The error message uses it.

### 4. Raise the shared error from the adapter

When the engine fails, raise `EngineUnavailableError`. Pass the stable error code, the adapter name, and a message. Do not return a default value. Do not catch the error and continue.

```python
raise EngineUnavailableError(
    "speech_engine_unavailable",
    self.engine_name,
    f"faster-whisper model '{self.model_size}' failed: {e}",
) from e
```

Use `engine_field="generator"` only when a published contract names the adapter key `generator`. The battlemap port does this for compatibility with TASK-0614.

### 5. Build the adapter at start-up

Build each engine in the app lifespan. A bad setting then stops the service at start-up. The first request does not find the error.

```python
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    get_speech_synthesizer()
    yield
```

Use a lazy singleton getter for the request path. The getter returns the injected test double when a test sets one.

### 6. Map the error to 503 once per app

Register the handler on the app. Do not catch the error in each route.

```python
from runefoble_platform.engine_ports import EngineUnavailableError, engine_unavailable_handler

app.add_exception_handler(EngineUnavailableError, engine_unavailable_handler)
```

The handler returns:

```json
{"detail": {"error": "speech_engine_unavailable", "engine": "faster-whisper", "message": "..."}}
```

The body sits under `detail`, as FastAPI `HTTPException` does. A WebSocket route cannot use the HTTP handler. It sends `error.body()` as a frame and keeps the socket open.

### 7. Inject a fake only in tests

Tests inject a fixture adapter at the composition root. Use the service setter, for example `set_speech_synthesizer`. Production code has no canned adapter. Do not add a fake to `build_adapter`'s registry.

Put the fixture under `tests/helpers/`. Write a failure test that sets the fixture to raise `EngineUnavailableError`. Assert the `503` status and the body keys.

When a test needs canned model output, do not add a canned adapter. Serve a loopback OpenAI-compatible endpoint instead. `tests/helpers/fake_openai_server.py` does this. The worker reaches it through its public `openai_compatible` setting. This is a true process boundary, so no code under test is replaced. The fixture `fake_llm` sets the reply text and records each request.

### 8. Write the frontdoor tests

Write a test for the public route. Assert:

- the status is `503`;
- the body names the error code and the engine;
- no output is stored or returned;
- no success event is published.

Write one test for an unknown setting value. The test must fail at start-up with a message that names the allowed values.

## Verify

Run only the tests for the service you changed and the shared library test:

```bash
uv run pytest -q -p no:randomly tests/test_engine_port_adapters.py tests/test_blackbox_<service>_<port>.py
```

## Known Gaps

- The rules compendium embedding provider does not map its errors to `503` yet. A provider failure returns `500`. Map it when the embedding port gets its own error contract.
- The wardrobe generator has no failure path. It has no `503`. Add the mapping when a generator can fail.
- The inference worker keeps its published flat body, `{"error": "backend_unavailable", "backend": "<name>"}`, with no `detail` wrapper and no `message` key. It registers its own handler in `api.py`. Its contract is `docs/reference/inference-worker-response-contract.md`. The worker also checks its engine once in the lifespan (`LLMPort.check_ready`). A port that fails that check stops start-up.
- The inference worker has no canned adapter. A `mock` value is refused, and the worker adds no keyword or template path. ADR-0015 decision 4 forbids those fallbacks in every environment.
- `campaign_lore` builds its ports with a `match` and `assert_never`. It is not yet on `build_adapter`.
- The Watcher builds its ports from the environment on each request (`load_watcher_ports` in `the_watcher/engine_selection.py`), not once as a singleton. The ports are not in the app container yet. `build_container` runs the same build once in the lifespan, so a bad setting stops start-up. Tests set the environment with `monkeypatch`. The worker adapters get `RUNEFOBLE_SERVICE_CREDENTIAL` from the same settings (`WatcherEngineSettings.service_credential`). Without it, a worker call answers `503`.
- The Watcher routes `compound.py` (speech parse) and the stand-in recap still call the local engine directly. They do not yet go through a port. The recap has no worker path.
