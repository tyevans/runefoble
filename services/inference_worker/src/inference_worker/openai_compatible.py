"""OpenAI-compatible chat adapter (llama-swap, vLLM, llama.cpp, and similar servers)."""

from typing import ClassVar

import httpx
import openai
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from inference_worker.ports import Completion, LLMPort, backend_unavailable

PROBE_TIMEOUT_SECONDS = 2.0

# Transport and API errors of the client library mean the backend is unavailable (503).
# Any other error is a defect. It propagates, and the app answers 500.
BACKEND_ERRORS: tuple[type[Exception], ...] = (openai.APIError, httpx.HTTPError)


async def probe_endpoint(engine: str, url: str) -> None:
    """GET `url` once. Raise EngineUnavailableError unless it answers 200."""
    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_SECONDS) as client:
            res = await client.get(url)
    except httpx.HTTPError as e:
        raise backend_unavailable(engine, f"probe of {url} failed: {e}") from e
    if res.status_code != 200:
        raise backend_unavailable(engine, f"probe of {url} returned {res.status_code}")


class OpenAICompatibleLLM(LLMPort):
    """Calls `POST {base_url}/chat/completions` on an OpenAI-compatible server."""

    engine_name: ClassVar[str] = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: SecretStr,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout_seconds: float,
    ) -> None:
        self._base_url = base_url
        self._chat = ChatOpenAI(
            base_url=base_url,
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_completion_tokens=max_tokens,
            timeout=timeout_seconds,
            # A retry would spend the budget twice. The caller's budget bounds the whole call.
            max_retries=0,
        )

    async def check_ready(self) -> None:
        await probe_endpoint(self.engine_name, f"{self._base_url}/models")

    async def complete(self, system_prompt: str, user_prompt: str) -> Completion:
        try:
            response = await self._chat.ainvoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            )
        except BACKEND_ERRORS as e:
            raise backend_unavailable(self.engine_name, str(e)) from e
        if response.response_metadata.get("finish_reason") == "length":
            raise backend_unavailable(
                self.engine_name, "model output stopped at the token limit (max_tokens)"
            )
        if not isinstance(response.content, str):
            raise backend_unavailable(self.engine_name, "model returned non-text content")
        return Completion(content=response.content, backend=self.engine_name)
