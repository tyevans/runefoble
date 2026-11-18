"""Ollama adapter. Ollama serves an OpenAI-compatible chat API under `/v1`."""

from typing import ClassVar

from pydantic import SecretStr

from inference_worker.openai_compatible import OpenAICompatibleLLM, probe_endpoint


class OllamaLLM(OpenAICompatibleLLM):
    engine_name: ClassVar[str] = "ollama"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout_seconds: float,
    ) -> None:
        super().__init__(
            base_url=f"{base_url}/v1",
            api_key=SecretStr("ollama"),
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )
        self._ollama_url = base_url

    async def check_ready(self) -> None:
        await probe_endpoint(self.engine_name, f"{self._ollama_url}/api/tags")
