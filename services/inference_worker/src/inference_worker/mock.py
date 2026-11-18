"""Mock adapter. It returns no model text. Graphs use canned output for source "mock".

The factory builds it only when the setting names `mock` explicitly.
"""

from typing import ClassVar

from inference_worker.ports import Completion, LLMPort


class MockLLM(LLMPort):
    engine_name: ClassVar[str] = "mock"

    async def check_ready(self) -> None:
        return None

    async def complete(self, system_prompt: str, user_prompt: str) -> Completion:
        return Completion(content="", backend=self.engine_name, source="mock")
