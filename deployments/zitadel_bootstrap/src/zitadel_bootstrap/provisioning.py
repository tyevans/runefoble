"""Idempotent provisioning of the Runefoble OIDC project and web application in Zitadel.

Zitadel generates the project ID and the client ID. The chart cannot know them at render
time, so the bootstrap Job asks the management API for them. Running `provision` again
creates nothing and changes nothing when the project and application already match.

Every request goes to the in-cluster origin with a `Host` header that names the issuer
host, the same rule the token verifier follows.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from runefoble_auth.zitadel import issuer_host_headers

MANAGEMENT_PREFIX = "/management/v1"
REQUEST_TIMEOUT_SECONDS = 10
READY_PATH = "/debug/healthz"
READY_POLL_SECONDS = 5
EQUALS = "TEXT_QUERY_METHOD_EQUALS"


class ZitadelBootstrapError(RuntimeError):
    """Zitadel refused a provisioning request. The message names the request and the status."""


@dataclass(frozen=True)
class ApplicationSpec:
    """The desired state of the project and the web application."""

    project_name: str
    app_name: str
    redirect_uris: tuple[str, ...]
    post_logout_redirect_uris: tuple[str, ...]
    dev_mode: bool


@dataclass(frozen=True)
class Provisioned:
    project_id: str
    app_id: str
    client_id: str


class ZitadelManagement:
    """Minimal client for the Zitadel v1 management API. Authenticates with a personal access token."""

    def __init__(self, issuer: str, internal_url: str, personal_access_token: str) -> None:
        self._origin = internal_url.rstrip("/")
        self._headers = {
            **issuer_host_headers(issuer),
            "Authorization": f"Bearer {personal_access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def wait_until_ready(self, timeout_seconds: float) -> None:
        """Poll Zitadel's health endpoint until it answers 200. Zitadel starts after the Job."""
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                self._send("GET", READY_PATH, headers=self._headers)
                return
            except ZitadelBootstrapError:
                if time.monotonic() >= deadline:
                    raise
            time.sleep(READY_POLL_SECONDS)

    def _request(
        self, method: str, path: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        raw = self._send(method, f"{MANAGEMENT_PREFIX}{path}", body, self._headers)
        return json.loads(raw) if raw.strip() else {}

    def _send(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            f"{self._origin}{path}", data=data, method=method, headers=headers or {}
        )
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return str(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise ZitadelBootstrapError(
                f"{method} {path} returned HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ZitadelBootstrapError(f"{method} {path} failed: {exc.reason}") from exc

    def find_project_id(self, name: str) -> str | None:
        result = self._request("POST", "/projects/_search", _name_query(name))
        return _first_id(result)

    def create_project(self, name: str) -> str:
        return str(self._request("POST", "/projects", {"name": name})["id"])

    def find_app_id(self, project_id: str, name: str) -> str | None:
        result = self._request("POST", f"/projects/{project_id}/apps/_search", _name_query(name))
        return _first_id(result)

    def get_oidc_config(self, project_id: str, app_id: str) -> dict[str, Any]:
        app = self._request("GET", f"/projects/{project_id}/apps/{app_id}")["app"]
        config: dict[str, Any] = app["oidcConfig"]
        return config

    def create_oidc_app(self, project_id: str, spec: ApplicationSpec) -> tuple[str, str]:
        created = self._request(
            "POST", f"/projects/{project_id}/apps/oidc", _oidc_body(spec, app_name=spec.app_name)
        )
        return str(created["appId"]), str(created["clientId"])

    def update_oidc_config(self, project_id: str, app_id: str, spec: ApplicationSpec) -> None:
        self._request("PUT", f"/projects/{project_id}/apps/{app_id}/oidc_config", _oidc_body(spec))

    def find_action(self, name: str) -> dict[str, Any] | None:
        query = {"queries": [{"actionNameQuery": {"name": name, "method": EQUALS}}]}
        matches = self._request("POST", "/actions/_search", query).get("result") or []
        return dict(matches[0]) if matches else None

    def create_action(self, action: dict[str, Any]) -> str:
        return str(self._request("POST", "/actions", action)["id"])

    def update_action(self, action_id: str, action: dict[str, Any]) -> None:
        self._request("PUT", f"/actions/{action_id}", action)

    def trigger_action_ids(self, flow_type: str, trigger_type: str) -> list[str]:
        """The IDs of the actions bound to one trigger of a flow, in execution order."""
        flow = self._request("GET", f"/flows/{flow_type}").get("flow") or {}
        for trigger in flow.get("triggerActions") or []:
            if str(trigger.get("triggerType", {}).get("id")) == trigger_type:
                return [str(action["id"]) for action in trigger.get("actions") or []]
        return []

    def set_trigger_actions(self, flow_type: str, trigger_type: str, action_ids: list[str]) -> None:
        """Replace the list of actions bound to one trigger of a flow."""
        self._request(
            "POST", f"/flows/{flow_type}/trigger/{trigger_type}", {"actionIds": action_ids}
        )


def provision(client: ZitadelManagement, spec: ApplicationSpec) -> Provisioned:
    """Create or find the project and the web application. Converge the URIs and dev mode."""
    project_id = client.find_project_id(spec.project_name) or client.create_project(
        spec.project_name
    )
    app_id = client.find_app_id(project_id, spec.app_name)
    if app_id is None:
        app_id, client_id = client.create_oidc_app(project_id, spec)
        return Provisioned(project_id=project_id, app_id=app_id, client_id=client_id)
    config = client.get_oidc_config(project_id, app_id)
    if _drifted(config, spec):
        client.update_oidc_config(project_id, app_id, spec)
    return Provisioned(project_id=project_id, app_id=app_id, client_id=str(config["clientId"]))


def _drifted(config: dict[str, Any], spec: ApplicationSpec) -> bool:
    return (
        set(config.get("redirectUris", [])) != set(spec.redirect_uris)
        or set(config.get("postLogoutRedirectUris", [])) != set(spec.post_logout_redirect_uris)
        or bool(config.get("devMode", False)) != spec.dev_mode
    )


def _name_query(name: str) -> dict[str, Any]:
    return {"queries": [{"nameQuery": {"name": name, "method": EQUALS}}]}


def _first_id(search_result: dict[str, Any]) -> str | None:
    matches = search_result.get("result") or []
    if not matches:
        return None
    return str(matches[0]["id"])


def _oidc_body(spec: ApplicationSpec, app_name: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "redirectUris": list(spec.redirect_uris),
        "postLogoutRedirectUris": list(spec.post_logout_redirect_uris),
        "responseTypes": ["OIDC_RESPONSE_TYPE_CODE"],
        "grantTypes": [
            "OIDC_GRANT_TYPE_AUTHORIZATION_CODE",
            "OIDC_GRANT_TYPE_REFRESH_TOKEN",
        ],
        "appType": "OIDC_APP_TYPE_USER_AGENT",
        "authMethodType": "OIDC_AUTH_METHOD_TYPE_NONE",
        "accessTokenType": "OIDC_TOKEN_TYPE_JWT",
        "accessTokenRoleAssertion": False,
        "idTokenRoleAssertion": False,
        "devMode": spec.dev_mode,
    }
    if app_name is not None:
        body["name"] = app_name
    return body
