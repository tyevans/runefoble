"""APIRouters for Game Session microservice."""

from game_session.routers.autopilot import router as autopilot_router
from game_session.routers.bounties import router as bounties_router
from game_session.routers.campfire import router as campfire_router
from game_session.routers.caravan_contracts import router as caravan_contracts_router
from game_session.routers.caravan_trade import router as caravan_trade_router
from game_session.routers.combat import router as combat_router
from game_session.routers.reactions import router as reactions_router
from game_session.routers.session import router as session_router
from game_session.routers.settlements import router as settlements_router
from game_session.routers.stronghold import router as stronghold_router
from game_session.routers.tavern import router as tavern_router
from game_session.routers.west_marches import router as west_marches_router

__all__ = [
    "autopilot_router",
    "bounties_router",
    "campfire_router",
    "caravan_contracts_router",
    "caravan_trade_router",
    "combat_router",
    "reactions_router",
    "session_router",
    "settlements_router",
    "stronghold_router",
    "tavern_router",
    "west_marches_router",
]
