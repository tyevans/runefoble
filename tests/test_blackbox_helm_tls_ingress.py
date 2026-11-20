"""Blackbox checks for the public TLS ingress and the HTTP-to-HTTPS redirect (TASK-0956).

The tests render the umbrella chart with `helm template` and read the manifests only. They
check exit codes, the key path named in a failure message, and the rendered Ingress and
Middleware objects.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.helpers.helm import helm_template_result, hosted_values_file, render_chart

APP_INGRESS = "runefoble-ingress"
REDIRECT_INGRESS = "runefoble-ingress-http-redirect"
MIDDLEWARE = "runefoble-https-redirect"
ENTRYPOINTS = "traefik.ingress.kubernetes.io/router.entrypoints"
MIDDLEWARES = "traefik.ingress.kubernetes.io/router.middlewares"
CLUSTER_ISSUER = "cert-manager.io/cluster-issuer"
RELEASE_NAMESPACE = "runefoble"


def _named(docs: list[dict], kind: str, name: str) -> list[dict]:
    return [doc for doc in docs if doc["kind"] == kind and doc["metadata"]["name"] == name]


def _one(docs: list[dict], kind: str, name: str) -> dict:
    found = _named(docs, kind, name)
    assert len(found) == 1, f"expected one {kind} named {name}, found {len(found)}"
    return found[0]


def _hosts(ingress: dict) -> list[str]:
    return [rule["host"] for rule in ingress["spec"]["rules"]]


def _render_hosted(tmp_path: Path, **overrides: Any) -> list[dict]:
    values = hosted_values_file(tmp_path, **overrides)
    return render_chart("-n", RELEASE_NAMESPACE, "-f", str(values))


def test_default_render_serves_http_only_without_tls():
    """The local render keeps HTTP on the web entrypoint. It has no TLS block and no redirect."""
    docs = render_chart()

    app = _one(docs, "Ingress", APP_INGRESS)
    assert "tls" not in app["spec"]
    assert app["metadata"]["annotations"][ENTRYPOINTS] == "web"
    assert _named(docs, "Middleware", MIDDLEWARE) == []
    assert _named(docs, "Ingress", REDIRECT_INGRESS) == []


def test_cert_manager_mode_adds_tls_for_every_host(tmp_path: Path):
    """certManager lists every app host in the TLS block and names the chosen ClusterIssuer."""
    docs = _render_hosted(
        tmp_path,
        **{"ingress.tls.mode": "certManager", "ingress.tls.clusterIssuer": "letsencrypt-prod"},
    )

    app = _one(docs, "Ingress", APP_INGRESS)
    assert app["spec"]["tls"] == [{"hosts": _hosts(app), "secretName": "runefoble-tls"}]
    assert app["metadata"]["annotations"][CLUSTER_ISSUER] == "letsencrypt-prod"


def test_existing_secret_mode_uses_operator_secret_and_no_issuer(tmp_path: Path):
    """existingSecret names the operator's TLS Secret and adds no cert-manager annotation."""
    docs = _render_hosted(
        tmp_path,
        **{"ingress.tls.mode": "existingSecret", "ingress.tls.secretName": "operator-wildcard"},
    )

    app = _one(docs, "Ingress", APP_INGRESS)
    assert app["spec"]["tls"] == [{"hosts": _hosts(app), "secretName": "operator-wildcard"}]
    assert CLUSTER_ISSUER not in app["metadata"]["annotations"]


def test_https_redirect_splits_entrypoints_and_adds_middleware(tmp_path: Path):
    """The redirect Middleware returns 301 to https. The app Ingress uses websecure only."""
    docs = _render_hosted(
        tmp_path,
        **{"ingress.tls.mode": "existingSecret", "ingress.tls.secretName": "operator-tls"},
    )

    middleware = _one(docs, "Middleware", MIDDLEWARE)
    assert middleware["apiVersion"] == "traefik.io/v1alpha1"
    assert middleware["spec"]["redirectScheme"] == {"scheme": "https", "permanent": True}

    app = _one(docs, "Ingress", APP_INGRESS)
    assert app["metadata"]["annotations"][ENTRYPOINTS] == "websecure"
    assert MIDDLEWARES not in app["metadata"]["annotations"]

    redirect = _one(docs, "Ingress", REDIRECT_INGRESS)
    assert redirect["metadata"]["annotations"][ENTRYPOINTS] == "web"
    assert redirect["metadata"]["annotations"][MIDDLEWARES] == (
        f"{RELEASE_NAMESPACE}-{MIDDLEWARE}@kubernetescrd"
    )
    assert _hosts(redirect) == _hosts(app)
    for rule in redirect["spec"]["rules"]:
        assert [p["path"] for p in rule["http"]["paths"]] == ["/"], (
            "the redirect Ingress must not proxy application paths over HTTP"
        )
    assert "tls" not in redirect["spec"]


@pytest.mark.parametrize(
    ("overrides", "key"),
    [
        ({"ingress.tls.mode": "none"}, "ingress.tls.mode"),
        ({"ingress.httpsRedirect": False}, "ingress.httpsRedirect"),
        (
            {"ingress.tls.mode": "certManager", "ingress.tls.clusterIssuer": "REPLACE-ME"},
            "ingress.tls.clusterIssuer",
        ),
        (
            {"ingress.tls.mode": "existingSecret", "ingress.tls.secretName": "REPLACE-ME"},
            "ingress.tls.secretName",
        ),
    ],
)
def test_hosted_render_rejects_missing_tls_or_redirect(
    tmp_path: Path, overrides: dict[str, Any], key: str
):
    """The guard fails a staging or production render that serves HTTP or uses a placeholder."""
    proc = helm_template_result("-f", str(hosted_values_file(tmp_path, **overrides)))

    assert proc.returncode != 0
    assert key in proc.stderr


@pytest.mark.parametrize(
    ("args", "key"),
    [
        (["--set", "ingress.httpsRedirect=true"], "ingress.tls.mode"),
        (["--set", "ingress.tls.mode=acme"], "ingress.tls.mode"),
        (["--set", "ingress.tls.mode=certManager"], "ingress.tls.clusterIssuer"),
        (["--set", "ingress.tls.mode=existingSecret"], "ingress.tls.secretName"),
    ],
)
def test_incomplete_tls_settings_fail_the_render(args: list[str], key: str):
    """A TLS setting with no source, or with no name, fails the render. It never falls back to HTTP."""
    proc = helm_template_result(*args)

    assert proc.returncode != 0
    assert key in proc.stderr
