"""Invite account route, public and without a bearer token (ADR-0023 d).

The route verifies the invite token and creates a Zitadel account for the given email. It
takes no bearer token, so it is the one campaign route that does not check identity. The
gateway rate limits it (ADR-0023 d). A password never passes through this route.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from game_session.campaign import service_accounts as accounts
from game_session.campaign.account_schemas import AccountRequestedResponse, CreateAccountRequest
from game_session.campaign.repositories import CampaignRepositories, campaign_repositories
from game_session.shared.container_access import app_container
from runefoble_auth.account_provisioner import AccountProvisioner
from starlette.requests import HTTPConnection

router = APIRouter(prefix="/api/v1/campaigns/invites", tags=["Campaigns & Sessions"])


def account_provisioner(conn: HTTPConnection) -> AccountProvisioner:
    """Return the account provisioner of the app container."""
    return app_container(conn).accounts


Repos = Annotated[CampaignRepositories, Depends(campaign_repositories)]
Provisioner = Annotated[AccountProvisioner, Depends(account_provisioner)]


@router.post(
    "/{token}/accounts",
    response_model=AccountRequestedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_account_from_invite(
    token: str,
    req: CreateAccountRequest,
    repos: Repos,
    provisioner: Provisioner,
) -> AccountRequestedResponse:
    """Create a Zitadel account through a valid invite. Zitadel emails the person to finish it."""
    return await accounts.request_account(repos, provisioner, token, req.email, req.display_name)
