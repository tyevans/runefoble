"""Build the account provisioner of game_session from settings (ADR-0023 c).

A service with no Zitadel service token gets an unconfigured provisioner. It answers every
request with the unavailable error, so the route returns 503 and creates nothing. A deployed
service refuses to start without the token (see `game_session.container`).
"""

from __future__ import annotations

import logging

from runefoble_auth.account_provisioner import (
    AccountProvisioner,
    AccountProvisionerUnavailableError,
    ProvisionedAccount,
)
from runefoble_auth.zitadel import issuer_host_headers
from runefoble_auth.zitadel_accounts import ZitadelAccountProvisioner
from runefoble_platform.config import PlatformSettings

logger = logging.getLogger("runefoble.game_session.accounts")


class UnconfiguredAccountProvisioner:
    """Stands in when no Zitadel service token is set. It never creates an account."""

    async def provision(self, email: str, display_name: str) -> ProvisionedAccount:
        logger.warning(
            "Account creation is not configured: RUNEFOBLE_ZITADEL_SERVICE_TOKEN is unset"
        )
        raise AccountProvisionerUnavailableError("The Zitadel service token is not configured")


def build_account_provisioner(settings: PlatformSettings) -> AccountProvisioner:
    """Return the Zitadel provisioner, or the unconfigured stand-in without a service token."""
    token = settings.zitadel_service_token
    if token is None or not token.get_secret_value().strip():
        return UnconfiguredAccountProvisioner()
    base_url = settings.zitadel_api_url or settings.zitadel_internal_url or settings.zitadel_issuer
    return ZitadelAccountProvisioner(
        base_url=base_url,
        service_token=token.get_secret_value(),
        org_id=settings.zitadel_org_id or None,
        host_headers=issuer_host_headers(settings.zitadel_issuer),
    )
