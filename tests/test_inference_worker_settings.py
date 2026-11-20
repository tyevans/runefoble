"""Blackbox checks for the inference worker's start-up settings (TASK-0948).

The worker reads its settings from the process environment at start-up. A blank API key
stops the start-up. No default fills a blank value.
"""

from __future__ import annotations

import pytest
from inference_worker.config import WorkerSettings
from pydantic import ValidationError

CREDENTIAL = "service-credential-for-tests-0123456789"


def test_worker_reads_hosted_settings_from_the_process_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RUNEFOBLE_SERVICE_CREDENTIAL", CREDENTIAL)
    monkeypatch.setenv("RUNEFOBLE_WORKER_OPENAI_API_KEY", "sk-hosted-test")
    monkeypatch.setenv("RUNEFOBLE_WORKER_OLLAMA_BASE_URL", "http://ollama.example.org:11434")
    monkeypatch.setenv("RUNEFOBLE_WORKER_OLLAMA_MODEL", "qwen-test")
    monkeypatch.setenv("RUNEFOBLE_WORKER_TEMPERATURE", "0.2")
    monkeypatch.setenv("RUNEFOBLE_WORKER_MAX_TOKENS", "256")
    monkeypatch.setenv("RUNEFOBLE_WORKER_TIMEOUT_SECONDS", "7.5")

    settings = WorkerSettings.from_environment()

    assert settings.openai_api_key.get_secret_value() == "sk-hosted-test"
    assert settings.ollama_base_url == "http://ollama.example.org:11434"
    assert settings.ollama_model == "qwen-test"
    assert settings.temperature == 0.2
    assert settings.max_tokens == 256
    assert settings.timeout_seconds == 7.5


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_api_key_stops_start_up(monkeypatch: pytest.MonkeyPatch, blank: str) -> None:
    monkeypatch.setenv("RUNEFOBLE_SERVICE_CREDENTIAL", CREDENTIAL)
    monkeypatch.setenv("RUNEFOBLE_WORKER_OPENAI_API_KEY", blank)

    with pytest.raises(ValidationError, match="OPENAI_API_KEY"):
        WorkerSettings.from_environment()
