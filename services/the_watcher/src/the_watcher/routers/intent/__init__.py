"""Modular intent router combining single speech, target disambiguation, and compound combo sub-routers."""

from __future__ import annotations

from fastapi import APIRouter
from the_watcher.routers.intent.compound import (
    execute_compound_actions,
    parse_intent_and_disambiguate,
)
from the_watcher.routers.intent.compound import (
    router as compound_router,
)
from the_watcher.routers.intent.disambiguation import (
    resolve_intent_disambiguation,
)
from the_watcher.routers.intent.disambiguation import (
    router as disambiguation_router,
)
from the_watcher.routers.intent.speech import (
    process_speech_action,
)
from the_watcher.routers.intent.speech import (
    router as speech_router,
)

router = APIRouter(tags=["intent"])
router.include_router(speech_router)
router.include_router(disambiguation_router)
router.include_router(compound_router)

__all__ = [
    "compound_router",
    "disambiguation_router",
    "execute_compound_actions",
    "parse_intent_and_disambiguate",
    "process_speech_action",
    "resolve_intent_disambiguation",
    "router",
    "speech_router",
]
