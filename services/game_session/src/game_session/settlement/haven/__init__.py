"""Settlement Haven Builder modular route package.

Governed by ADR-0001, ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

from game_session.settlement.haven.loaders import (
    build_settlement_projection,
    load_establishment,
    load_settlement,
    save_and_publish,
    to_uuid,
)
from game_session.settlement.haven.routes_establishments import (
    construct_establishment,
    get_establishment,
    list_settlement_establishments,
)
from game_session.settlement.haven.routes_establishments import (
    router as establishments_router,
)
from game_session.settlement.haven.routes_havens import (
    found_settlement,
    get_campaign_settlement_projection,
    list_campaign_settlements,
)
from game_session.settlement.haven.routes_havens import router as havens_router
from game_session.settlement.haven.routes_upgrades import (
    router as upgrades_router,
)
from game_session.settlement.haven.routes_upgrades import (
    upgrade_establishment,
    upgrade_settlement_tier,
)

__all__ = [
    "build_settlement_projection",
    "construct_establishment",
    "establishments_router",
    "found_settlement",
    "get_campaign_settlement_projection",
    "get_establishment",
    "havens_router",
    "list_campaign_settlements",
    "list_settlement_establishments",
    "load_establishment",
    "load_settlement",
    "save_and_publish",
    "to_uuid",
    "upgrade_establishment",
    "upgrade_settlement_tier",
    "upgrades_router",
]
