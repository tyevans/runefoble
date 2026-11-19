"""Authentication router package for Runefoble Gateway API.

Zitadel issues every token. The gateway mounts only the profile routes here. The profile
paths are absolute (/api/v1/profile), so this router carries no prefix.
"""

from fastapi import APIRouter
from gateway_api.routers.auth.profile import (
    UpdateProfileRequest,
    update_profile,
)
from gateway_api.routers.auth.profile import (
    router as profile_router,
)

router = APIRouter(tags=["User Profile"])

router.include_router(profile_router)


__all__ = [
    "UpdateProfileRequest",
    "profile_router",
    "router",
    "update_profile",
]
