"""Use case: an invite link creates the player account (ADR-0023 b, c, d).

Order of work, so that a refused request changes nothing:
1. Find the invite. Unknown token: 404, no provider call.
2. Check that the invite is usable (not expired, uses left). Otherwise 410, no provider call.
3. Ask the identity provider for the account. Provider failure: 503, nothing recorded.
4. Only for a new account: record one use and the pending join, in one save.

An existing email records nothing. That person joins later through the normal join route.
"""

from __future__ import annotations

from game_session.campaign.account_schemas import AccountRequestedResponse
from game_session.campaign.errors import AccountProviderUnavailableError, InviteNotFoundError
from game_session.campaign.invite_aggregate import invite_stream_id
from game_session.campaign.repositories import CampaignRepositories, concurrent_update
from runefoble_auth.account_provisioner import (
    AccountProvisioner,
    AccountProvisionerUnavailableError,
    ProvisionedAccount,
)
from runefoble_platform.aggregate_loading import load_if_exists, save_or_conflict
from runefoble_platform.models import utc_now


async def request_account(
    repos: CampaignRepositories,
    provisioner: AccountProvisioner,
    token: str,
    email: str,
    display_name: str,
) -> AccountRequestedResponse:
    invite = await load_if_exists(repos.invites, invite_stream_id(token))
    if invite is None:
        raise InviteNotFoundError("Invite token does not exist")
    now = utc_now()
    invite.ensure_redeemable(now)

    account = await _provision(provisioner, email, display_name)
    if account.created:
        invite.redeem(account.user_id, now)
        invite.record_pending(account.user_id, invite.state.role)
        await save_or_conflict(repos.invites, invite, concurrent_update)
    return AccountRequestedResponse()


async def _provision(
    provisioner: AccountProvisioner, email: str, display_name: str
) -> ProvisionedAccount:
    try:
        return await provisioner.provision(email, display_name)
    except AccountProvisionerUnavailableError as exc:
        raise AccountProviderUnavailableError("The account provider is unavailable") from exc
