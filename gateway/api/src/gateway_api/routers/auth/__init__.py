"""Authentication and Email Registration router package for Runefoble Gateway API.

Aggregates modular auth sub-routers into a unified APIRouter mounted at /api/v1/auth.
"""

from fastapi import APIRouter
from gateway_api.routers.auth.admin import (
    invite_admin_or_dm,
    seed_dev_admin,
)
from gateway_api.routers.auth.admin import (
    router as admin_router,
)
from gateway_api.routers.auth.dev_mail import (
    _mailpit_client,
    clear_dev_emails,
    get_mailpit_client,
    list_dev_emails,
    mailpit_status,
    send_test_email,
    set_mailpit_client,
)
from gateway_api.routers.auth.dev_mail import (
    router as dev_mail_router,
)
from gateway_api.routers.auth.profile import (
    UpdateProfileRequest,
    get_profile,
    update_profile,
)
from gateway_api.routers.auth.profile import (
    router as profile_router,
)
from gateway_api.routers.auth.registration import (
    _pending_verifications,
    register_user,
    resend_verification,
    verify_email,
)
from gateway_api.routers.auth.registration import (
    router as registration_router,
)
from gateway_api.routers.auth.schemas import (
    DevSendEmailRequest,
    InviteAdminRequest,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    SeedAdminRequest,
    TestEmailRequest,
    TokenRequest,
    VerifyEmailRequest,
)
from gateway_api.routers.auth.tokens import (
    _generate_mock_jwt,
    login_for_token,
    logout_user,
    refresh_token,
)
from gateway_api.routers.auth.tokens import (
    router as tokens_router,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & Signups"])

router.include_router(registration_router)
router.include_router(tokens_router)
router.include_router(dev_mail_router)
router.include_router(admin_router)
router.include_router(profile_router)


__all__ = [
    "DevSendEmailRequest",
    "InviteAdminRequest",
    "PasswordResetRequest",
    "RefreshRequest",
    "RegisterRequest",
    "SeedAdminRequest",
    "TestEmailRequest",
    "TokenRequest",
    "VerifyEmailRequest",
    "_generate_mock_jwt",
    "_mailpit_client",
    "_pending_verifications",
    "admin_router",
    "clear_dev_emails",
    "dev_mail_router",
    "get_mailpit_client",
    "invite_admin_or_dm",
    "list_dev_emails",
    "login_for_token",
    "logout_user",
    "mailpit_status",
    "refresh_token",
    "register_user",
    "registration_router",
    "resend_verification",
    "router",
    "seed_dev_admin",
    "send_test_email",
    "set_mailpit_client",
    "tokens_router",
    "verify_email",
    "profile_router",
    "UpdateProfileRequest",
    "get_profile",
    "update_profile",
]
