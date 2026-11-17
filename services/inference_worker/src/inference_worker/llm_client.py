"""Multi-backend LLM client for Runefoble AI Inference Worker."""

import json
import logging
import re
from typing import Any

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from inference_worker.config import WorkerSettings

logger = logging.getLogger("runefoble.inference.llm_client")

UNAVAILABLE_BACKEND = "unavailable"


class InferenceBackendError(Exception):
    """Raised when the selected inference backend cannot produce a usable result.

    The API maps this error to HTTP 503 with `error: backend_unavailable`.
    """

    def __init__(self, backend: str, reason: str) -> None:
        super().__init__(f"inference backend '{backend}' unavailable: {reason}")
        self.backend = backend
        self.reason = reason


def parse_json_object(content: str) -> dict[str, Any]:
    """Extract the first JSON object from model output. Return an empty dict if none parses."""
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


class MultiBackendLLMClient:
    """Manages connection to local GPU model runtimes. The mock backend is explicit only."""

    def __init__(self, settings: WorkerSettings | None = None) -> None:
        self.settings = settings or WorkerSettings()
        self._active_backend: str = self.settings.backend

    async def _probe(self, url: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(url)
        except httpx.HTTPError as e:
            logger.debug("Backend probe failed for %s: %s", url, e)
            return False
        return res.status_code == 200

    async def detect_available_backend(self) -> str:
        """Select the configured backend. In auto mode, probe for a live model server."""
        if self.settings.backend != "auto":
            return self.settings.backend

        if await self._probe(f"{self.settings.openai_base_url}/models"):
            logger.info(
                "Detected active OpenAI-compatible backend at %s",
                self.settings.openai_base_url,
            )
            return "openai_compatible"

        if await self._probe(f"{self.settings.ollama_base_url}/api/tags"):
            logger.info("Detected active Ollama backend at %s", self.settings.ollama_base_url)
            return "ollama"

        logger.error(
            "No active GPU model server detected. Inference is unavailable. "
            "Set RUNEFOBLE_WORKER_BACKEND=mock to use canned output explicitly."
        )
        return UNAVAILABLE_BACKEND

    def _build_chat_model(self, backend: str) -> BaseChatModel | None:
        if backend == "openai_compatible":
            return ChatOpenAI(
                base_url=self.settings.openai_base_url,
                api_key=self.settings.openai_api_key.get_secret_value(),
                model=self.settings.openai_model,
                temperature=self.settings.temperature,
                max_tokens=self.settings.max_tokens,
                timeout=self.settings.timeout_seconds,
            )
        if backend == "ollama":
            # Ollama exposes OpenAI-compatible /v1/chat/completions as well
            return ChatOpenAI(
                base_url=f"{self.settings.ollama_base_url}/v1",
                api_key="ollama",
                model=self.settings.ollama_model,
                temperature=self.settings.temperature,
                max_tokens=self.settings.max_tokens,
                timeout=self.settings.timeout_seconds,
            )
        return None

    @property
    def active_backend(self) -> str:
        return self._active_backend

    async def generate_completion(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Generate a completion. Return `source` "llm" or "mock".

        Raise InferenceBackendError when a real backend is unavailable or fails.
        Never substitute canned text for a failed backend.
        """
        backend = await self.detect_available_backend()
        self._active_backend = backend

        if backend == "mock":
            return {"success": True, "content": "", "backend": "mock", "source": "mock"}

        model = self._build_chat_model(backend)
        if model is None:
            raise InferenceBackendError(backend, "no model server available")

        try:
            response = await model.ainvoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            )
        except Exception as e:
            logger.error("Model backend %s failed: %s", backend, e)
            raise InferenceBackendError(backend, str(e)) from e

        return {
            "success": True,
            "content": response.content,
            "backend": backend,
            "source": "llm",
        }
