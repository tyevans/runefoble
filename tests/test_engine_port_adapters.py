"""Shared engine-port adapter selection and the 503 contract for unavailable engines.

These tests drive the public functions of `runefoble_platform.engine_ports` and the
voice agent start-up path. They use no private state.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from runefoble_platform.engine_ports import (
    EngineUnavailableError,
    UnknownAdapterError,
    build_adapter,
    engine_unavailable_handler,
)


class _Adapter:
    def __init__(self, label: str = "default") -> None:
        self.label = label


def test_build_adapter_returns_the_registered_factory_product() -> None:
    adapter = build_adapter(
        "RUNEFOBLE_TEST_ENGINE",
        "alpha",
        {"alpha": lambda: _Adapter("from-alpha"), "beta": _Adapter},
    )

    assert isinstance(adapter, _Adapter)
    assert adapter.label == "from-alpha"


def test_build_adapter_rejects_unknown_value_and_names_the_allowed_values() -> None:
    built: list[str] = []

    def factory_alpha() -> _Adapter:
        built.append("alpha")
        return _Adapter()

    with pytest.raises(UnknownAdapterError) as info:
        build_adapter(
            "RUNEFOBLE_TEST_ENGINE",
            "gamma",
            {"beta": _Adapter, "alpha": factory_alpha},
        )

    message = str(info.value)
    assert "RUNEFOBLE_TEST_ENGINE" in message
    assert "'gamma'" in message
    assert "'alpha'" in message
    assert "'beta'" in message
    assert built == [], "no factory may run for an unknown value"


def test_unknown_adapter_error_is_a_value_error() -> None:
    assert issubclass(UnknownAdapterError, ValueError)


def test_unavailable_engine_maps_to_503_with_error_code_and_engine() -> None:
    app = FastAPI()
    app.add_exception_handler(EngineUnavailableError, engine_unavailable_handler)

    @app.get("/speak")
    async def speak() -> None:
        raise EngineUnavailableError(
            "speech_engine_unavailable", "faster-whisper", "model failed to load"
        )

    response = TestClient(app).get("/speak")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "error": "speech_engine_unavailable",
            "engine": "faster-whisper",
            "message": "model failed to load",
        }
    }


def test_engine_unavailable_error_keeps_its_fields() -> None:
    exc = EngineUnavailableError("map_generation_unavailable", "fixture", "offline")

    assert exc.error_code == "map_generation_unavailable"
    assert exc.engine == "fixture"
    assert str(exc) == "offline"


def test_voice_agent_rejects_unknown_stt_engine_at_start_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unknown speech engine stops the voice agent at start-up and names the allowed value."""
    from voice_agent.main import app
    from voice_agent.stt import set_streaming_pipeline

    monkeypatch.setenv("RUNEFOBLE_VOICE_STT_ENGINE", "not-an-engine")
    set_streaming_pipeline(None)

    with pytest.raises(ValidationError, match="faster-whisper"), TestClient(app):
        pass
