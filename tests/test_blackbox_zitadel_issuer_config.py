"""Blackbox checks for Zitadel issuer consistency in the rendered Helm chart.

The tests render the umbrella chart and read the public manifests only. The browser-facing
issuer must equal the `iss` value that Zitadel writes, and every service must use it.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

HELM_CHART = Path("deployments/helm/runefoble")
EXPECTED_ISSUER = "http://auth.localhost"
EXPECTED_JWKS_URL = "http://zitadel:8080/oauth/v2/keys"
ZITADEL_HOST = "auth.localhost"


def _render() -> list[dict]:
    if not shutil.which("helm"):
        pytest.skip("helm CLI not available")
    proc = subprocess.run(
        ["helm", "template", "runefoble", str(HELM_CHART)],
        capture_output=True,
        text=True,
        check=True,
    )
    return [doc for doc in yaml.safe_load_all(proc.stdout) if doc]


def _find(docs: list[dict], kind: str, name: str) -> dict:
    found = next(
        (d for d in docs if d.get("kind") == kind and d.get("metadata", {}).get("name") == name),
        None,
    )
    assert found is not None, f"{kind} {name} not found in rendered chart"
    return found


def _env_map(container: dict) -> dict[str, str]:
    return {item["name"]: item.get("value") for item in container.get("env", [])}


def test_zitadel_writes_browser_facing_external_domain():
    """Zitadel serves the browser-facing host, port, and protocol, so `iss` matches the issuer."""
    docs = _render()
    container = _find(docs, "Deployment", "zitadel")["spec"]["template"]["spec"]["containers"][0]
    env = _env_map(container)
    assert env.get("ZITADEL_EXTERNALDOMAIN") == ZITADEL_HOST
    assert env.get("ZITADEL_EXTERNALPORT") == "80"
    assert env.get("ZITADEL_EXTERNALSECURE") == "false"


def test_every_service_uses_the_browser_facing_issuer_and_internal_jwks():
    """All deployments that verify tokens share one issuer and one in-cluster JWKS URL."""
    docs = _render()
    checked = []
    for doc in docs:
        if doc.get("kind") != "Deployment":
            continue
        for container in doc["spec"]["template"]["spec"]["containers"]:
            env = _env_map(container)
            if "RUNEFOBLE_ZITADEL_ISSUER" not in env:
                continue
            checked.append(doc["metadata"]["name"])
            assert env["RUNEFOBLE_ZITADEL_ISSUER"] == EXPECTED_ISSUER, doc["metadata"]["name"]
            assert env["RUNEFOBLE_ZITADEL_JWKS_URL"] == EXPECTED_JWKS_URL, doc["metadata"]["name"]
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


def test_runtime_config_is_rendered_from_values_and_mounted_into_nginx():
    """The frontend serves /runtime-config.json with the issuer, client ID, and scopes."""
    docs = _render()
    config_map = _find(docs, "ConfigMap", "frontend-runtime-config")
    runtime = json.loads(config_map["data"]["runtime-config.json"])
    assert runtime["issuer"] == EXPECTED_ISSUER
    assert runtime["clientId"] == ""
    assert runtime["scopes"] == ["openid", "profile", "email", "offline_access"]
    assert runtime["providerName"] == "Zitadel"
    assert "client_secret" not in config_map["data"]["runtime-config.json"]

    deployment = _find(docs, "Deployment", "frontend")
    pod = deployment["spec"]["template"]["spec"]
    mounts = pod["containers"][0]["volumeMounts"]
    assert {
        "name": "runtime-config",
        "mountPath": "/usr/share/nginx/html/runtime-config.json",
        "subPath": "runtime-config.json",
        "readOnly": True,
    } in mounts
    volume = next(v for v in pod["volumes"] if v["name"] == "runtime-config")
    assert volume["configMap"]["name"] == "frontend-runtime-config"
