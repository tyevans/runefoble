"""The intent port adapter that runs the grammar first (ADR-0022 a, b, c).

The grammar parses every transcript. A result that is not `narrative` returns as it is. Its
`source` is `watcher_rules`. A `narrative` result goes to the LLM intent engine when one is
configured, and the LLM result returns with its own `source`. Without an LLM engine the player
hears "Not understood." and no action is invented.

A failure is never retried elsewhere. A grammar error propagates and the worker is not called.
A worker failure propagates as its `EngineUnavailableError` (HTTP 503), and the grammar does not
run again. The routing order is fixed before the call, so it is not a fallback (ADR-0015).
"""

from __future__ import annotations

from the_watcher.models import IntentResult, SpeechInputRequest
from the_watcher.ports import IntentParser
from the_watcher.watcher_ai import TheWatcherEngine

NARRATIVE = "narrative"
NOT_UNDERSTOOD = "Not understood."


class GrammarFirstIntentParser(IntentParser):
    """Parses with the grammar. Sends only the grammar's `narrative` results to `llm`."""

    engine_name = "watcher_rules"

    def __init__(self, grammar: TheWatcherEngine, llm: IntentParser | None) -> None:
        self._grammar = grammar
        self._llm = llm

    async def parse(self, req: SpeechInputRequest, authorization: str | None) -> IntentResult:
        result = self._grammar.parse_speech_intent(req.transcript, req.speaker_name)
        if result.action_type != NARRATIVE:
            return result
        if self._llm is None:
            return IntentResult(action_type=NARRATIVE, watcher_reply=NOT_UNDERSTOOD)
        return await self._llm.parse(req, authorization)
