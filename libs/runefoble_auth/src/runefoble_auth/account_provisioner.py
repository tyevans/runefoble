"""Port that creates a player account in the identity provider (ADR-0023 c).

`game_session` depends on this port. The Zitadel adapter (`zitadel_accounts.py`) implements it.
A caller never receives a password or a Zitadel init code. Zitadel sends the email itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProvisionedAccount:
    """The identity provider user for one email.

    `created` is True when this call created the user. It is False when the email already had
    a user. In that case the provider sent a sign-in or password-reset email instead.
    """

    user_id: str
    created: bool


class AccountProvisionerUnavailableError(Exception):
    """The identity provider could not create or find the account. Nothing was created here.

    The caller answers 503. The provisioner never falls back to a local user.
    """


class AccountProvisioner(Protocol):
    async def provision(self, email: str, display_name: str) -> ProvisionedAccount: ...
