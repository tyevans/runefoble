"""Idempotent set-up of the Zitadel Action that puts `preferred_username` in access tokens.

Zitadel JWT access tokens carry no `preferred_username`. The services verify the access
token, so without this Action `VerifiedPrincipal.username` is `None` for every sign-in.

The Action uses Zitadel Actions v1 (Zitadel v2.54): flow "Complement Token" (id `2`),
trigger "Pre access token creation" (id `5`). Zitadel calls the script function whose name
is the action name. `api.v1.claims.setClaim` does not replace a claim that is already set.

Actions v1 belong to one organization. Zitadel runs the flow of the organization that owns
the user. The bootstrap token belongs to the default organization, so the flow applies to the
users of that organization.
"""

from __future__ import annotations

from typing import Any

from zitadel_bootstrap.provisioning import ZitadelManagement

COMPLEMENT_TOKEN_FLOW = "2"
PRE_ACCESS_TOKEN_CREATION = "5"
ACTION_NAME = "runefobleUsernameClaim"
ACTION_TIMEOUT = "10s"
ACTION_SCRIPT = f"""function {ACTION_NAME}(ctx, api) {{
  var user = ctx.v1.getUser();
  if (user && user.username) {{
    api.v1.claims.setClaim('preferred_username', user.username);
  }}
}}
"""


def username_claim_action() -> dict[str, Any]:
    """The desired state of the Action. A failure stops token creation, so no error is hidden."""
    return {
        "name": ACTION_NAME,
        "script": ACTION_SCRIPT,
        "timeout": ACTION_TIMEOUT,
        "allowedToFail": False,
    }


def ensure_username_claim_action(client: ZitadelManagement) -> str:
    """Create or converge the Action and bind it to the trigger. Returns the action ID.

    A second run with no drift sends no write request. Other actions on the trigger stay bound.
    """
    desired = username_claim_action()
    existing = client.find_action(ACTION_NAME)
    if existing is None:
        action_id = client.create_action(desired)
    else:
        action_id = str(existing["id"])
        if _drifted(existing, desired):
            client.update_action(action_id, desired)
    bound = client.trigger_action_ids(COMPLEMENT_TOKEN_FLOW, PRE_ACCESS_TOKEN_CREATION)
    if action_id not in bound:
        client.set_trigger_actions(
            COMPLEMENT_TOKEN_FLOW, PRE_ACCESS_TOKEN_CREATION, [*bound, action_id]
        )
    return action_id


def _drifted(existing: dict[str, Any], desired: dict[str, Any]) -> bool:
    # The JSON gateway can leave out a false boolean, so a missing `allowedToFail` is false.
    return (
        existing.get("name") != desired["name"]
        or existing.get("script") != desired["script"]
        or existing.get("timeout") != desired["timeout"]
        or bool(existing.get("allowedToFail", False)) != desired["allowedToFail"]
    )
