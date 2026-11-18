"""LLM port of the inference worker. Adapters implement it. Graphs depend on it only.

An adapter raises `EngineUnavailableError` when its engine cannot produce a result. It never
returns substitute text. See docs/how-to/add-an-engine-port-adapter.md.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Literal

from runefoble_platform.engine_ports import EngineUnavailableError

BACKEND_UNAVAILABLE = "backend_unavailable"

CompletionSource = Literal["llm", "mock"]


@dataclass(frozen=True)
class Completion:
    """One model result. `source` is "llm" for a real engine and "mock" for canned output."""

    content: str
    backend: str
    source: CompletionSource


def backend_unavailable(backend: str, message: str) -> EngineUnavailableError:
    """Build the error that the worker reports as HTTP 503 with `error` and `backend` keys."""
    return EngineUnavailableError(BACKEND_UNAVAILABLE, backend, message, engine_field="backend")


class LLMPort(ABC):
    """A chat model engine. Each adapter names its engine in `engine_name`."""

    engine_name: ClassVar[str]

    @abstractmethod
    async def check_ready(self) -> None:
        """Confirm that the engine answers. Runs once at start-up.

        Raises EngineUnavailableError when the engine does not answer.
        """

    @abstractmethod
    async def complete(self, system_prompt: str, user_prompt: str) -> Completion:
        """Return one completion.

        Raises EngineUnavailableError when the engine fails or returns no usable content.
        """
