"""Install an LLM port into the inference worker app for one test.

The worker builds its port once in the app lifespan. Tests install a port through the same
public setter, and pytest restores the module globals when the test ends.
"""

from __future__ import annotations

import pytest
from inference_worker import api
from inference_worker.ports import LLMPort

_WORKER_GLOBALS = ("llm_port", "intent_graph", "narration_graph", "stand_in_graph")


def install_worker_port(monkeypatch: pytest.MonkeyPatch, port: LLMPort) -> None:
    """Make `port` the worker's LLM port. Graphs are rebuilt for it."""
    for name in _WORKER_GLOBALS:
        monkeypatch.setattr(api, name, getattr(api, name))
    api.set_llm_port(port)
