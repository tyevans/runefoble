"""Builds the worker's LLM port from settings. Called once from the app lifespan."""

from collections.abc import Callable

from runefoble_platform.engine_ports import build_adapter

from inference_worker.config import WorkerSettings
from inference_worker.mock import MockLLM
from inference_worker.ollama import OllamaLLM
from inference_worker.openai_compatible import OpenAICompatibleLLM
from inference_worker.ports import LLMPort


def build_llm_port(settings: WorkerSettings) -> LLMPort:
    """Build the adapter that `RUNEFOBLE_WORKER_BACKEND` selects. Unknown values raise."""
    registry: dict[str, Callable[[], LLMPort]] = {
        "openai_compatible": lambda: OpenAICompatibleLLM(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            timeout_seconds=settings.timeout_seconds,
        ),
        "ollama": lambda: OllamaLLM(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            timeout_seconds=settings.timeout_seconds,
        ),
        "mock": MockLLM,
    }
    return build_adapter("RUNEFOBLE_WORKER_BACKEND", settings.backend, registry)
