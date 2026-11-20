"""Frontdoor tests for the Zitadel bootstrap Job.

The Job runs `main` with its environment. Zitadel and the Kubernetes API are external
processes, so each test runs them as local HTTP servers. The fake Zitadel refuses any
request whose Host header is not the issuer host, as the real instance does.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from helpers.local_http_server import LocalHttpServer, RecordedRequest
from zitadel_bootstrap import provisioning
from zitadel_bootstrap.job import BootstrapConfigError, main
from zitadel_bootstrap.provisioning import ZitadelBootstrapError

ISSUER = "http://auth.localhost"
ADMIN_PAT = "pat-bootstrap-admin"
REDIRECT = "http://localhost/auth/callback"
POST_LOGOUT = "http://localhost/"


class FakeZitadel:
    """Keeps projects and applications in memory, as the management API does."""

    def __init__(self, starting_checks: int = 0) -> None:
        self.projects: dict[str, str] = {}
        self.apps: dict[tuple[str, str], dict[str, Any]] = {}
        self.actions: dict[str, dict[str, Any]] = {}
        self.triggers: dict[tuple[str, str], list[str]] = {}
        self.starting_checks = starting_checks
        self.health_checks = 0
        self._next = 0
        self.login_policy: dict[str, Any] = {
            "allowUsernamePassword": True,
            "allowRegister": True,
            "allowExternalIdp": True,
            "passwordCheckLifetime": "864000s",
        }
        self.policy_writes: list[dict[str, Any]] = []
        self.policy_refusal: tuple[int, Any] | None = None

    def _id(self, prefix: str) -> str:
        self._next += 1
        return f"{prefix}-{self._next}"

    def __call__(self, request: RecordedRequest) -> tuple[int, Any]:
        if request.headers.get("Host") != "auth.localhost":
            return 404, {"message": "Instance not found"}
        if request.path == "/debug/healthz":
            self.health_checks += 1
            return (
                (503, {"message": "starting"})
                if self.health_checks <= self.starting_checks
                else (200, {})
            )
        if request.headers.get("Authorization") != f"Bearer {ADMIN_PAT}":
            return 401, {"message": "unauthenticated"}
        parts = request.path.split("/")  # ["", "management", "v1", ...] or ["", "admin", "v1", ...]
        if parts[1] == "admin":
            return self._login_policy_route(request, parts[2:])
        if request.method == "POST" and parts[3:] == ["projects", "_search"]:
            return 200, {"result": self._search_projects(request)}
        if request.method == "POST" and parts[3:] == ["projects"]:
            project_id = self._id("proj")
            self.projects[request.json()["name"]] = project_id
            return 200, {"id": project_id}
        if len(parts) >= 7 and parts[3] == "projects" and parts[5] == "apps":
            return self._app_route(request, parts[4], parts[6:])
        if parts[3] == "actions":
            return self._action_route(request, parts[4:])
        if parts[3] == "flows":
            return self._flow_route(request, parts[4:])
        return 404, {"message": f"no route for {request.method} {request.path}"}

    def _search_projects(self, request: RecordedRequest) -> list[dict[str, str]]:
        name = request.json()["queries"][0]["nameQuery"]["name"]
        return [{"id": self.projects[name], "name": name}] if name in self.projects else []

    def _app_route(
        self, request: RecordedRequest, project_id: str, rest: list[str]
    ) -> tuple[int, Any]:
        if request.method == "POST" and rest == ["_search"]:
            name = request.json()["queries"][0]["nameQuery"]["name"]
            app = self.apps.get((project_id, name))
            return 200, {"result": [{"id": app["id"], "name": name}] if app else []}
        if request.method == "POST" and rest == ["oidc"]:
            body = request.json()
            app_id, client_id = self._id("app"), self._id("client")
            self.apps[(project_id, body["name"])] = {
                "id": app_id,
                "clientId": client_id,
                "oidcConfig": {k: v for k, v in body.items() if k != "name"},
            }
            return 200, {"appId": app_id, "clientId": client_id}
        app = self._app_by_id(project_id, rest[0]) if rest else None
        if request.method == "GET" and len(rest) == 1 and app is not None:
            config = {**app["oidcConfig"], "clientId": app["clientId"]}
            return 200, {"app": {"id": app["id"], "oidcConfig": config}}
        if request.method == "PUT" and rest[1:] == ["oidc_config"] and app is not None:
            app["oidcConfig"] = request.json()
            return 200, {}
        return 404, {"message": f"no app route for {request.method} {request.path}"}

    def add_action(self, name: str, script: str) -> str:
        action_id = self._id("action")
        self.actions[action_id] = {
            "id": action_id,
            "name": name,
            "script": script,
            "timeout": "10s",
            "allowedToFail": False,
        }
        return action_id

    def _action_route(self, request: RecordedRequest, rest: list[str]) -> tuple[int, Any]:
        if request.method == "POST" and rest == ["_search"]:
            name = request.json()["queries"][0]["actionNameQuery"]["name"]
            return 200, {"result": [a for a in self.actions.values() if a["name"] == name]}
        if request.method == "POST" and rest == []:
            body = request.json()
            action_id = self.add_action(body["name"], body["script"])
            self.actions[action_id].update(body)
            return 200, {"id": action_id}
        if request.method == "PUT" and len(rest) == 1 and rest[0] in self.actions:
            self.actions[rest[0]].update({k: v for k, v in request.json().items() if k != "id"})
            return 200, {}
        return 404, {"message": f"no action route for {request.method} {request.path}"}

    def _flow_route(self, request: RecordedRequest, rest: list[str]) -> tuple[int, Any]:
        if request.method == "GET" and len(rest) == 1:
            trigger_actions = [
                {
                    "triggerType": {"id": trigger},
                    "actions": [self.actions[action_id] for action_id in ids],
                }
                for (flow, trigger), ids in self.triggers.items()
                if flow == rest[0] and ids
            ]
            return 200, {"flow": {"type": {"id": rest[0]}, "triggerActions": trigger_actions}}
        if request.method == "POST" and len(rest) == 3 and rest[1] == "trigger":
            self.triggers[(rest[0], rest[2])] = list(request.json()["actionIds"])
            return 200, {}
        return 404, {"message": f"no flow route for {request.method} {request.path}"}

    def _login_policy_route(self, request: RecordedRequest, rest: list[str]) -> tuple[int, Any]:
        if rest != ["v1", "policies", "login"]:
            return 404, {"message": f"no admin route for {request.method} {request.path}"}
        if self.policy_refusal is not None:
            return self.policy_refusal
        if request.method == "GET":
            return 200, {"policy": dict(self.login_policy)}
        if request.method == "PUT":
            self.login_policy = request.json()
            self.policy_writes.append(request.json())
            return 200, {}
        return 404, {"message": f"no admin route for {request.method} {request.path}"}

    def _app_by_id(self, project_id: str, app_id: str) -> dict[str, Any] | None:
        return next(
            (
                app
                for (pid, _), app in self.apps.items()
                if pid == project_id and app["id"] == app_id
            ),
            None,
        )


class FakeKubernetes:
    """Records server-side apply requests for Secrets."""

    def __init__(self) -> None:
        self.applied: list[RecordedRequest] = []

    def __call__(self, request: RecordedRequest) -> tuple[int, Any]:
        if request.method == "PATCH" and "/secrets/" in request.path:
            self.applied.append(request)
            return 200, request.json()
        return 404, {"message": "not found"}

    def last_data(self) -> dict[str, str]:
        assert self.applied, "no Secret was applied"
        return self.applied[-1].json()["stringData"]


@pytest.fixture
def service_account(tmp_path: Path) -> Path:
    (tmp_path / "token").write_text("kube-token-test\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def zitadel():
    fake = FakeZitadel()
    with LocalHttpServer(fake) as server:
        yield fake, server


@pytest.fixture
def kubernetes():
    fake = FakeKubernetes()
    with LocalHttpServer(fake) as server:
        yield fake, server


def job_env(zitadel_url: str, kube_url: str, **overrides: str) -> dict[str, str]:
    env = {
        "RUNEFOBLE_ZITADEL_ISSUER": ISSUER,
        "RUNEFOBLE_ZITADEL_INTERNAL_URL": zitadel_url,
        "ZITADEL_ADMIN_PAT": ADMIN_PAT,
        "POD_NAMESPACE": "runefoble",
        "RUNEFOBLE_ZITADEL_CLIENT_SECRET_NAME": "runefoble-zitadel-client",
        "RUNEFOBLE_ZITADEL_PROJECT_NAME": "runefoble",
        "RUNEFOBLE_ZITADEL_APP_NAME": "runefoble-web",
        "RUNEFOBLE_ZITADEL_REDIRECT_URIS": REDIRECT,
        "RUNEFOBLE_ZITADEL_POST_LOGOUT_URIS": POST_LOGOUT,
        "RUNEFOBLE_ZITADEL_DEV_MODE": "true",
        "RUNEFOBLE_ZITADEL_CLOSED_REGISTRATION": "false",
        "KUBERNETES_API_URL": kube_url,
    }
    env.update(overrides)
    return env


def test_first_run_creates_the_project_and_app_and_publishes_their_ids(
    zitadel, kubernetes, service_account: Path
) -> None:
    fake_zitadel, zitadel_server = zitadel
    fake_kube, kube_server = kubernetes

    exit_code = main(job_env(zitadel_server.url, kube_server.url), service_account)

    assert exit_code == 0
    assert list(fake_zitadel.projects) == ["runefoble"]
    app = fake_zitadel.apps[("proj-1", "runefoble-web")]
    assert app["oidcConfig"]["authMethodType"] == "OIDC_AUTH_METHOD_TYPE_NONE"
    assert app["oidcConfig"]["accessTokenType"] == "OIDC_TOKEN_TYPE_JWT"
    assert app["oidcConfig"]["redirectUris"] == [REDIRECT]
    assert app["oidcConfig"]["postLogoutRedirectUris"] == [POST_LOGOUT]
    assert fake_kube.last_data() == {"project-id": "proj-1", "client-id": app["clientId"]}


def test_job_waits_while_zitadel_is_still_starting(
    kubernetes, service_account: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_zitadel = FakeZitadel(starting_checks=2)
    monkeypatch.setattr(provisioning, "READY_POLL_SECONDS", 0)
    _, kube_server = kubernetes
    with LocalHttpServer(fake_zitadel) as zitadel_server:
        assert main(job_env(zitadel_server.url, kube_server.url), service_account) == 0

    assert fake_zitadel.health_checks == 3
    assert list(fake_zitadel.projects) == ["runefoble"]


def test_every_request_to_zitadel_names_the_issuer_host(
    zitadel, kubernetes, service_account: Path
) -> None:
    fake_zitadel, zitadel_server = zitadel
    _, kube_server = kubernetes

    main(job_env(zitadel_server.url, kube_server.url), service_account)

    assert zitadel_server.requests, "the Job made no management requests"
    assert {req.headers.get("Host") for req in zitadel_server.requests} == {"auth.localhost"}


def test_second_run_creates_nothing_and_applies_the_same_ids(
    zitadel, kubernetes, service_account: Path
) -> None:
    fake_zitadel, zitadel_server = zitadel
    fake_kube, kube_server = kubernetes
    env = job_env(zitadel_server.url, kube_server.url)
    main(env, service_account)
    first_data = fake_kube.last_data()
    zitadel_server.requests.clear()

    assert main(env, service_account) == 0

    writes = [
        req
        for req in zitadel_server.requests
        if req.method in ("POST", "PUT") and "_search" not in req.path
    ]
    assert writes == [], "a second run must not create or update Zitadel objects"
    assert fake_kube.last_data() == first_data
    assert len(fake_zitadel.projects) == 1
    assert len(fake_zitadel.apps) == 1
    assert len(fake_zitadel.actions) == 1


def test_changed_redirect_uris_update_the_existing_app_without_a_second_app(
    zitadel, kubernetes, service_account: Path
) -> None:
    fake_zitadel, zitadel_server = zitadel
    _, kube_server = kubernetes
    main(job_env(zitadel_server.url, kube_server.url), service_account)
    changed = "https://play.runefoble.example/auth/callback"

    main(
        job_env(zitadel_server.url, kube_server.url, RUNEFOBLE_ZITADEL_REDIRECT_URIS=changed),
        service_account,
    )

    assert len(fake_zitadel.apps) == 1
    assert fake_zitadel.apps[("proj-1", "runefoble-web")]["oidcConfig"]["redirectUris"] == [changed]


def test_missing_setting_is_named_in_the_error(zitadel, kubernetes, service_account: Path) -> None:
    _, zitadel_server = zitadel
    _, kube_server = kubernetes
    env = job_env(zitadel_server.url, kube_server.url)
    del env["ZITADEL_ADMIN_PAT"]

    with pytest.raises(BootstrapConfigError, match="ZITADEL_ADMIN_PAT"):
        main(env, service_account)


COMPLEMENT_TOKEN_FLOW = "2"
PRE_ACCESS_TOKEN_TRIGGER = "5"


def test_first_run_binds_a_username_claim_action_to_access_token_creation(
    zitadel, kubernetes, service_account: Path
) -> None:
    fake_zitadel, zitadel_server = zitadel
    _, kube_server = kubernetes

    main(job_env(zitadel_server.url, kube_server.url), service_account)

    bound = fake_zitadel.triggers[(COMPLEMENT_TOKEN_FLOW, PRE_ACCESS_TOKEN_TRIGGER)]
    assert len(bound) == 1
    action = fake_zitadel.actions[bound[0]]
    # Zitadel calls the function whose name is the action name.
    assert f"function {action['name']}(ctx, api)" in action["script"]
    assert "api.v1.claims.setClaim('preferred_username'" in action["script"]
    assert "ctx.v1.getUser()" in action["script"]
    assert action["allowedToFail"] is False


def test_other_actions_on_the_trigger_stay_bound(
    zitadel, kubernetes, service_account: Path
) -> None:
    fake_zitadel, zitadel_server = zitadel
    _, kube_server = kubernetes
    other = fake_zitadel.add_action("addTenantClaim", "function addTenantClaim(ctx, api) {}")
    fake_zitadel.triggers[(COMPLEMENT_TOKEN_FLOW, PRE_ACCESS_TOKEN_TRIGGER)] = [other]

    main(job_env(zitadel_server.url, kube_server.url), service_account)

    bound = fake_zitadel.triggers[(COMPLEMENT_TOKEN_FLOW, PRE_ACCESS_TOKEN_TRIGGER)]
    assert bound[0] == other
    assert len(bound) == 2


def test_a_changed_action_script_is_updated_in_place(
    zitadel, kubernetes, service_account: Path
) -> None:
    fake_zitadel, zitadel_server = zitadel
    _, kube_server = kubernetes
    main(job_env(zitadel_server.url, kube_server.url), service_account)
    (action_id,) = fake_zitadel.actions
    expected_script = fake_zitadel.actions[action_id]["script"]
    fake_zitadel.actions[action_id]["script"] = "function stale(ctx, api) {}"

    main(job_env(zitadel_server.url, kube_server.url), service_account)

    assert list(fake_zitadel.actions) == [action_id]
    assert fake_zitadel.actions[action_id]["script"] == expected_script
    assert fake_zitadel.triggers[(COMPLEMENT_TOKEN_FLOW, PRE_ACCESS_TOKEN_TRIGGER)] == [action_id]


def test_closed_registration_turns_off_local_sign_up_and_keeps_other_login_settings(
    zitadel, kubernetes, service_account: Path
) -> None:
    fake_zitadel, zitadel_server = zitadel
    _, kube_server = kubernetes

    exit_code = main(
        job_env(zitadel_server.url, kube_server.url, RUNEFOBLE_ZITADEL_CLOSED_REGISTRATION="true"),
        service_account,
    )

    assert exit_code == 0
    policy = fake_zitadel.login_policy
    assert policy["allowRegister"] is False
    assert policy["allowUsernamePassword"] is True
    assert policy["allowExternalIdp"] is True
    assert policy["passwordCheckLifetime"] == "864000s"


def test_closed_registration_on_a_second_run_writes_the_policy_once(
    zitadel, kubernetes, service_account: Path
) -> None:
    fake_zitadel, zitadel_server = zitadel
    _, kube_server = kubernetes
    env = job_env(zitadel_server.url, kube_server.url, RUNEFOBLE_ZITADEL_CLOSED_REGISTRATION="true")

    main(env, service_account)
    main(env, service_account)

    assert len(fake_zitadel.policy_writes) == 1


def test_open_registration_leaves_the_login_policy_untouched(
    zitadel, kubernetes, service_account: Path
) -> None:
    fake_zitadel, zitadel_server = zitadel
    _, kube_server = kubernetes

    main(job_env(zitadel_server.url, kube_server.url), service_account)

    assert fake_zitadel.policy_writes == []
    assert fake_zitadel.login_policy["allowRegister"] is True


def test_refused_login_policy_read_fails_the_job(
    zitadel, kubernetes, service_account: Path
) -> None:
    fake_zitadel, zitadel_server = zitadel
    _, kube_server = kubernetes
    fake_zitadel.policy_refusal = (403, {"message": "permission denied"})

    with pytest.raises(ZitadelBootstrapError, match="policies/login returned HTTP 403"):
        main(
            job_env(
                zitadel_server.url, kube_server.url, RUNEFOBLE_ZITADEL_CLOSED_REGISTRATION="true"
            ),
            service_account,
        )

    assert fake_zitadel.policy_writes == []
