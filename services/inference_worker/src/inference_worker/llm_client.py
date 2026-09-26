"""Multi-backend LLM client for Runefoble AI Inference Worker."""

import logging
from typing import Any

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from inference_worker.config import WorkerSettings

logger = logging.getLogger("runefoble.inference.llm_client")


class MultiBackendLLMClient:
    """Manages connection to local GPU model runtimes or mock fallbacks."""

    def __init__(self, settings: WorkerSettings | None = None) -> None:
        self.settings = settings or WorkerSettings()
        self._active_backend: str = self.settings.backend
        self._cached_client: BaseChatModel | None = None

    async def detect_available_backend(self) -> str:
        """Probe available backends on the host and select the best working one."""
        if self.settings.backend != "auto":
            return self.settings.backend

        # Probe 1: OpenAI-compatible (llama-swap / vLLM)
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.settings.openai_base_url}/models")
                if res.status_code == 200:
                    logger.info(
                        "Detected active OpenAI-compatible backend at %s",
                        self.settings.openai_base_url,
                    )
                    return "openai_compatible"
        except Exception:
            pass

        # Probe 2: Ollama
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.settings.ollama_base_url}/api/tags")
                if res.status_code == 200:
                    logger.info(
                        "Detected active Ollama backend at %s",
                        self.settings.ollama_base_url,
                    )
                    return "ollama"
        except Exception:
            pass

        logger.info("No active GPU model server detected. Operating in mock fallback mode.")
        return "mock"

    async def get_chat_model(self) -> BaseChatModel | None:
        """Instantiate LangChain ChatModel corresponding to the active backend."""
        backend = await self.detect_available_backend()
        self._active_backend = backend

        if backend == "openai_compatible":
            return ChatOpenAI(
                base_url=self.settings.openai_base_url,
                api_key=self.settings.openai_api_key.get_secret_value(),
                model=self.settings.openai_model,
                temperature=self.settings.temperature,
                max_tokens=self.settings.max_tokens,
                timeout=self.settings.timeout_seconds,
            )
        elif backend == "ollama":
            # Ollama exposes OpenAI-compatible /v1/chat/completions as well
            return ChatOpenAI(
                base_url=f"{self.settings.ollama_base_url}/v1",
                api_key="ollama",
                model=self.settings.ollama_model,
                temperature=self.settings.temperature,
                max_tokens=self.settings.max_tokens,
                timeout=self.settings.timeout_seconds,
            )
        else:
            return None

    @property
    def active_backend(self) -> str:
        return self._active_backend

    async def generate_completion(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Generate response via active backend or deterministic mock."""
        model = await self.get_chat_model()
        if model is not None:
            try:
                from langchain_core.messages import HumanMessage, SystemMessage

                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
                response = await model.ainvoke(messages)
                return {
                    "success": True,
                    "content": response.content,
                    "backend": self._active_backend,
                }
            except Exception as e:
                logger.warning(
                    "Error invoking model backend %s: %s. Using fallback.", self._active_backend, e
                )

        # Mock fallback
        return {
            "success": True,
            "content": f"[Generated response for prompt: {user_prompt[:50]}...]",
            "backend": "mock",
        }
