"""Modular DM Co-Pilot router combining whisper and action interceptor sub-routers."""

from __future__ import annotations

from fastapi import APIRouter
from the_watcher.routers.copilot.actions import (
    approve_action,
    list_pending_actions,
    modify_action,
    propose_action,
    veto_action,
)
from the_watcher.routers.copilot.actions import (
    router as actions_router,
)
from the_watcher.routers.copilot.whispers import (
    create_whisper,
    generate_whispers,
    get_whispers,
)
from the_watcher.routers.copilot.whispers import (
    router as whispers_router,
)

router = APIRouter()
router.include_router(actions_router)
router.include_router(whispers_router)

__all__ = [
    "actions_router",
    "approve_action",
    "create_whisper",
    "generate_whispers",
    "get_whispers",
    "list_pending_actions",
    "modify_action",
    "propose_action",
    "router",
    "veto_action",
    "whispers_router",
]
