"""Aggregator APIRouter for settlement haven builder and establishment aggregates.

Governed by ADR-0001, ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

from fastapi import APIRouter
from game_session.settlement.bulletin_router import (
    decrypt_cipher_notice,
    list_bulletin_notices,
    pin_bulletin_notice,
    remove_bulletin_notice,
)
from game_session.settlement.bulletin_router import router as bulletin_router
from game_session.settlement.haven.routes_establishments import router as establishments_router
from game_session.settlement.haven.routes_havens import router as havens_router
from game_session.settlement.haven.routes_upgrades import router as upgrades_router

router = APIRouter(tags=["settlement-haven-builder"])
for sub_router in (havens_router, establishments_router, upgrades_router, bulletin_router):
    router.include_router(sub_router)

__all__ = [
    "bulletin_router",
    "decrypt_cipher_notice",
    "establishments_router",
    "havens_router",
    "list_bulletin_notices",
    "pin_bulletin_notice",
    "remove_bulletin_notice",
    "router",
    "upgrades_router",
]
