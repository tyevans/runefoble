"""Zitadel adapter of the `AccountProvisioner` port (ADR-0023 b, c).

The adapter calls the Zitadel user API of the chart image (v2.54, served under `/v2beta`). Each
call sends the service token as a bearer token.

- `POST /v2beta/users` (ListUsers) with an email query finds a user that already has the email.
- `POST /v2beta/users/human` (AddHumanUser) creates a user with no password and a verified address.
- `POST /v2beta/users/{id}/password_reset` (`sendLink`) sends the one mail: the Set Password link.
  A new user and an existing user both get it, so the reply is the same for both.

Runefoble never sends or stores a password or an init code. A failed call raises
`AccountProvisionerUnavailableError`. The adapter logs the operation and the HTTP status only.
It never logs the email, the token, or a Zitadel reply body.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from runefoble_auth.account_provisioner import (
    AccountProvisionerUnavailableError,
    ProvisionedAccount,
)

logger = logging.getLogger("runefoble.auth.zitadel_accounts")

REQUEST_TIMEOUT_S = 5.0
STATUS_USER_EXISTS = 409
# The user service path of the chart Zitadel image (v2.54.0). It serves the user API under
# /v2beta; /v2 answers 404 there (checked on Kind, 2026-11-20). Change it with the image.
USER_API = "/v2beta"
EMAIL_EQUALS_IGNORE_CASE = "TEXT_QUERY_METHOD_EQUALS_IGNORE_CASE"


class _UserAlreadyExistsError(Exception):
    """Zitadel refused a create because the user exists. Internal to the adapter."""


class ZitadelAccountProvisioner:
    """Create or find a Zitadel user for an email. Implements `AccountProvisioner`."""

    def __init__(
        self,
        *,
        base_url: str,
        service_token: str,
        org_id: str | None = None,
        host_headers: dict[str, str] | None = None,
        timeout_s: float = REQUEST_TIMEOUT_S,
    ) -> None:
        if not base_url.strip():
            raise ValueError("The Zitadel API URL is not set (RUNEFOBLE_ZITADEL_API_URL)")
        if not service_token.strip():
            raise ValueError(
                "The Zitadel service token is not set (RUNEFOBLE_ZITADEL_SERVICE_TOKEN)"
            )
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._headers: dict[str, str] = {
            "Authorization": f"Bearer {service_token}",
            "Accept": "application/json",
            **(host_headers or {}),
        }
        if org_id:
            self._headers["x-zitadel-orgid"] = org_id

    async def provision(self, email: str, display_name: str) -> ProvisionedAccount:
        existing = await self._find_user_id(email)
        if existing is not None:
            await self._send_reset_link(existing)
            return ProvisionedAccount(user_id=existing, created=False)
        try:
            user_id = await self._create_user(email, display_name)
        except _UserAlreadyExistsError:
            # Another request created this user after the search. Treat it as an existing user.
            existing = await self._find_user_id(email)
            if existing is None:
                raise AccountProvisionerUnavailableError(
                    "Zitadel reports a user that the search cannot find"
                ) from None
            await self._send_reset_link(existing)
            return ProvisionedAccount(user_id=existing, created=False)
        await self._send_reset_link(user_id)
        return ProvisionedAccount(user_id=user_id, created=True)

    async def _find_user_id(self, email: str) -> str | None:
        body = {
            "queries": [{"emailQuery": {"emailAddress": email, "method": EMAIL_EQUALS_IGNORE_CASE}}]
        }
        document = await self._expect_json("search", f"{USER_API}/users", body, status_ok={200})
        # Zitadel leaves `result` out of the reply when no user matches (protobuf JSON omits an
        # empty list), so a missing key means no match. Any other shape is an error.
        results = document.get("result", [])
        if not isinstance(results, list):
            raise _unavailable("search", "the reply has no result list")
        if not results:
            return None
        return _string_field(results[0], "userId", "search")

    async def _create_user(self, email: str, display_name: str) -> str:
        given, family = _split_name(display_name)
        body = {
            "username": email,
            "profile": {"givenName": given, "familyName": family, "displayName": display_name},
            # No verify-code mail. The one mail is the Set Password link sent after the create.
            # Only the owner of the mailbox can use it, so the address is marked verified here
            # (ADR-0023 b). A person who cannot read the mailbox can never sign in.
            "email": {"email": email, "isVerified": True},
        }
        response = await self._send("create", f"{USER_API}/users/human", body)
        if response.status_code == STATUS_USER_EXISTS:
            raise _UserAlreadyExistsError()
        document = _json_object("create", response)
        return _string_field(document, "userId", "create")

    async def _send_reset_link(self, user_id: str) -> None:
        body = {"sendLink": {"notificationType": "NOTIFICATION_TYPE_EMAIL"}}
        await self._expect_json(
            "password_reset", f"{USER_API}/users/{user_id}/password_reset", body, status_ok={200}
        )

    async def _expect_json(
        self, operation: str, path: str, body: dict[str, Any], *, status_ok: set[int]
    ) -> dict[str, Any]:
        response = await self._send(operation, path, body)
        if response.status_code not in status_ok:
            _log_rejection(operation, response.status_code)
            raise _unavailable(operation, f"HTTP {response.status_code}")
        return _json_object(operation, response)

    async def _send(self, operation: str, path: str, body: dict[str, Any]) -> httpx.Response:
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as http:
                return await http.post(f"{self._base_url}{path}", json=body, headers=self._headers)
        except httpx.HTTPError as exc:
            logger.warning("Zitadel %s could not be reached: %s", operation, type(exc).__name__)
            raise AccountProvisionerUnavailableError(
                f"Zitadel {operation} could not be reached"
            ) from exc


def _split_name(display_name: str) -> tuple[str, str]:
    """Zitadel needs a given and a family name. A single word fills both."""
    parts = display_name.split(None, 1)
    given = parts[0]
    family = parts[1] if len(parts) > 1 else parts[0]
    return given, family


def _json_object(operation: str, response: httpx.Response) -> dict[str, Any]:
    if response.status_code >= 300:
        _log_rejection(operation, response.status_code)
        raise _unavailable(operation, f"HTTP {response.status_code}")
    try:
        document = response.json()
    except ValueError as exc:
        raise _unavailable(operation, "the reply is not JSON") from exc
    if not isinstance(document, dict):
        raise _unavailable(operation, "the reply is not a JSON object")
    return document


def _string_field(document: Any, name: str, operation: str) -> str:
    value = document.get(name) if isinstance(document, dict) else None
    if not isinstance(value, str) or not value:
        raise _unavailable(operation, f"the reply has no {name}")
    return value


def _log_rejection(operation: str, status_code: int) -> None:
    logger.warning("Zitadel %s was rejected with HTTP %d", operation, status_code)


def _unavailable(operation: str, reason: str) -> AccountProvisionerUnavailableError:
    return AccountProvisionerUnavailableError(f"Zitadel {operation} failed: {reason}")
