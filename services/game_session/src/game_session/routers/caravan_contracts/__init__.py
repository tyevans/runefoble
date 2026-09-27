"""Modular Caravan Contracts router combining board and lifecycle sub-routers."""

from __future__ import annotations

from fastapi import APIRouter
from game_session.routers.caravan_contracts.auth import (
    _check_high_tier_auth,
    _check_perm,
    _to_uuid,
)
from game_session.routers.caravan_contracts.board import (
    get_caravan_contract,
    list_caravan_contracts,
    post_caravan_contract,
)
from game_session.routers.caravan_contracts.board import (
    router as board_router,
)
from game_session.routers.caravan_contracts.lifecycle import (
    accept_caravan_contract,
    dispatch_contract_caravan,
    fulfill_caravan_contract,
    report_contract_ambush,
)
from game_session.routers.caravan_contracts.lifecycle import (
    router as lifecycle_router,
)

router = APIRouter()
router.include_router(board_router)
router.include_router(lifecycle_router)

__all__ = [
    "_check_high_tier_auth",
    "_check_perm",
    "_to_uuid",
    "accept_caravan_contract",
    "board_router",
    "dispatch_contract_caravan",
    "fulfill_caravan_contract",
    "get_caravan_contract",
    "lifecycle_router",
    "list_caravan_contracts",
    "post_caravan_contract",
    "report_contract_ambush",
    "router",
]
