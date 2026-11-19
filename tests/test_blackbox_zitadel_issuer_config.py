"""Blackbox checks for Zitadel issuer, audience, and bootstrap wiring in the rendered Helm chart.

The tests render the umbrella chart and read the public manifests only. The browser-facing
issuer must equal the `iss` value that Zitadel writes, and every service must use it. The
audience and client ID come from the Secret that the bootstrap Job writes.
"""

import json

from tests.helpers.helm import render_chart

EXPECTED_ISSUER = "http://auth.localhost"
EXPECTED_INTERNAL_URL = "http://zitadel:8080"
CLIENT_SECRET = "runefoble-zitadel-client"
ZITADEL_HOST = "auth.localhost"


def _render() -> list[dict]:
    return render_chart()


def _find(docs: list[dict], kind: str, name: str) -> dict:
    found = next(
        (d for d in docs if d.get("kind") == kind and d.get("metadata", {}).get("name") == name),
        None,
    )
    assert found is not None, f"{kind} {name} not found in rendered chart"
    return found


def _env_map(container: dict) -> dict[str, str]:
    return {item["name"]: item.get("value") for item in container.get("env", [])}


def _env_entry(container: dict, name: str) -> dict:
    return next(item for item in container.get("env", []) if item["name"] == name)


def test_zitadel_writes_browser_facing_external_domain():
    """Zitadel serves the browser-facing host, port, and protocol, so `iss` matches the issuer."""
    docs = _render()
    container = _find(docs, "Deployment", "zitadel")["spec"]["template"]["spec"]["containers"][0]
    env = _env_map(container)
    assert env.get("ZITADEL_EXTERNALDOMAIN") == ZITADEL_HOST
    assert env.get("ZITADEL_EXTERNALPORT") == "80"
    assert env.get("ZITADEL_EXTERNALSECURE") == "false"


def test_every_service_uses_the_browser_facing_issuer_internal_url_and_project_audience():
    """All deployments that verify tokens share one issuer, one in-cluster origin, and the project audience."""
    docs = _render()
    checked = []
    for doc in docs:
        if doc.get("kind") != "Deployment":
            continue
        for container in doc["spec"]["template"]["spec"]["containers"]:
            env = _env_map(container)
            if "RUNEFOBLE_ZITADEL_ISSUER" not in env:
                continue
            name = doc["metadata"]["name"]
            checked.append(name)
            assert env["RUNEFOBLE_ZITADEL_ISSUER"] == EXPECTED_ISSUER, name
            assert env["RUNEFOBLE_ZITADEL_INTERNAL_URL"] == EXPECTED_INTERNAL_URL, name
            assert "RUNEFOBLE_ZITADEL_JWKS_URL" not in env, name
            audience = _env_entry(container, "RUNEFOBLE_ZITADEL_AUDIENCE")
            assert audience["valueFrom"]["secretKeyRef"] == {
                "name": CLIENT_SECRET,
                "key": "project-id",
            }, name
    assert "gateway-api" in checked
    assert "asset-forge" in checked


def test_zitadel_host_is_routed_to_zitadel_and_not_under_a_path():
    """The Zitadel host routes its root path to zitadel:8080. No /auth path remains."""
    docs = _render()
    ingress = _find(docs, "Ingress", "runefoble-ingress")
    rules = {rule["host"]: rule["http"]["paths"] for rule in ingress["spec"]["rules"]}
    assert ZITADEL_HOST in rules, "no ingress host for Zitadel"
    zitadel_paths = rules[ZITADEL_HOST]
    assert [(p["path"], p["backend"]["service"]["name"]) for p in zitadel_paths] == [
        ("/", "zitadel")
    ]
    for host, paths in rules.items():
        assert all(p["path"] != "/auth" for p in paths), f"host {host} still routes /auth"


def test_runtime_config_template_takes_client_and_project_ids_from_the_secret():
    """The frontend init container fills the generated IDs into the runtime config at start."""
    docs = _render()
    config_map = _find(docs, "ConfigMap", "frontend-runtime-config")
    runtime = json.loads(config_map["data"]["runtime-config.json"])
    assert runtime["issuer"] == EXPECTED_ISSUER
    assert runtime["clientId"] == "__RUNEFOBLE_CLIENT_ID__"
    assert runtime["scopes"] == [
        "openid",
        "profile",
        "email",
        "offline_access",
        "urn:zitadel:iam:org:project:id:__RUNEFOBLE_PROJECT_ID__:aud",
    ]
    assert runtime["providerName"] == "Zitadel"
    assert "client_secret" not in config_map["data"]["runtime-config.json"]

    deployment = _find(docs, "Deployment", "frontend")
    pod = deployment["spec"]["template"]["spec"]
    init = pod["initContainers"][0]
    init_env = {item["name"]: item["valueFrom"]["secretKeyRef"] for item in init["env"]}
    assert init_env == {
        "RUNEFOBLE_CLIENT_ID": {"name": CLIENT_SECRET, "key": "client-id"},
        "RUNEFOBLE_PROJECT_ID": {"name": CLIENT_SECRET, "key": "project-id"},
    }
    mounts = pod["containers"][0]["volumeMounts"]
    assert {
        "name": "runtime-config",
        "mountPath": "/usr/share/nginx/html/runtime-config.json",
        "subPath": "runtime-config.json",
        "readOnly": True,
    } in mounts
    volume = next(v for v in pod["volumes"] if v["name"] == "runtime-config")
    assert volume == {"name": "runtime-config", "emptyDir": {}}


def test_bootstrap_job_runs_after_install_with_the_admin_token_from_a_secret():
    """The bootstrap Job is a post-install hook. It reads the admin token from a Secret, not the Zitadel container."""
    docs = _render()
    job = _find(docs, "Job", "zitadel-bootstrap")
    hook = job["metadata"]["annotations"]["helm.sh/hook"]
    assert hook == "post-install,post-upgrade"
    container = job["spec"]["template"]["spec"]["containers"][0]
    env = _env_map(container)
    assert env["RUNEFOBLE_ZITADEL_ISSUER"] == EXPECTED_ISSUER
    assert env["RUNEFOBLE_ZITADEL_INTERNAL_URL"] == EXPECTED_INTERNAL_URL
    assert env["RUNEFOBLE_ZITADEL_CLIENT_SECRET_NAME"] == CLIENT_SECRET
    assert env["RUNEFOBLE_ZITADEL_PROJECT_NAME"] == "runefoble"
    assert env["RUNEFOBLE_ZITADEL_APP_NAME"] == "runefoble-web"
    assert env["RUNEFOBLE_ZITADEL_REDIRECT_URIS"] == "http://localhost/auth/callback"
    assert env["RUNEFOBLE_ZITADEL_POST_LOGOUT_URIS"] == "http://localhost/"
    assert _env_entry(container, "ZITADEL_ADMIN_PAT")["valueFrom"]["secretKeyRef"] == {
        "name": "zitadel-admin",
        "key": "pat",
    }


def test_bootstrap_role_may_write_only_the_client_secret_by_name():
    """RBAC grants create on Secrets, and get or patch only on the client Secret by name."""
    docs = _render()
    role = _find(docs, "Role", "zitadel-bootstrap")
    named = [rule for rule in role["rules"] if rule.get("resourceNames")]
    assert named == [
        {
            "apiGroups": [""],
            "resources": ["secrets"],
            "resourceNames": [CLIENT_SECRET],
            "verbs": ["get", "patch"],
        }
    ]
    binding = _find(docs, "RoleBinding", "zitadel-bootstrap")
    assert binding["subjects"][0]["name"] == "zitadel-bootstrap"


def test_bootstrap_job_is_omitted_when_disabled():
    """Set zitadel.bootstrap.enabled=false for the first install, before the admin token exists."""
    docs = render_chart("--set", "zitadel.bootstrap.enabled=false")
    assert not any(
        doc.get("kind") == "Job" and doc["metadata"]["name"] == "zitadel-bootstrap" for doc in docs
    )
