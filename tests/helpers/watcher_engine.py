"""Select The Watcher's engine through its public settings in a blackbox test."""

from __future__ import annotations

from typing import Any

import pytest


def select_worker_engine(monkeypatch: pytest.MonkeyPatch, worker_url: str | None) -> None:
    """Make The Watcher call the inference worker at `worker_url`. None leaves the URL unset."""
    monkeypatch.setenv("RUNEFOBLE_WATCHER_ENGINE", "inference_worker")
    if worker_url is None:
        monkeypatch.delenv("RUNEFOBLE_INFERENCE_URL", raising=False)
    else:
        monkeypatch.setenv("RUNEFOBLE_INFERENCE_URL", worker_url)


def error_fields(detail: dict[str, Any]) -> dict[str, Any]:
    """Return the stable error fields of a 503 body. The free-text `message` is not part of them."""
    return {key: value for key, value in detail.items() if key != "message"}
