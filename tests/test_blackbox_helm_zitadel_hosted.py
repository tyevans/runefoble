"""Blackbox render checks for Zitadel SMTP, closed registration and the public issuer (TASK-0958).

The tests render the umbrella chart with `helm template`. They read the rendered Zitadel pod,
the bootstrap Job and the guard failure messages. They do not read the chart templates.
The local render keeps Mailpit. The hosted render uses the SMTP provider from values and reads
the SMTP password from the credentials Secret.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.helpers.helm import (
    helm_template_result,
    hosted_values_file,
    render_chart,
)

TEAM_SECRET = "team-credentials"
SMTP_HOST = "smtp.hosted-test.invalid"
SMTP_FROM = "noreply@hosted-test.invalid"
ZITADEL_ENV_PREFIX = "ZITADEL_DEFAULTINSTANCE_SMTPCONFIGURATION_"


def _doc(docs: list[dict[str, Any]], kind: str, name: str) -> dict[str, Any]:
    return next(doc for doc in docs if doc["kind"] == kind and doc["metadata"]["name"] == name)


def _env(container: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["name"]: item for item in container.get("env", [])}


def _zitadel_env(docs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    deployment = _doc(docs, "Deployment", "zitadel")
    return _env(deployment["spec"]["template"]["spec"]["containers"][0])


def _bootstrap_env(docs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    job = _doc(docs, "Job", "zitadel-bootstrap")
    return _env(job["spec"]["template"]["spec"]["containers"][0])


def _hosted_docs(tmp_path: Path, **overrides: object) -> list[dict[str, Any]]:
    values = {"credentials.existingSecret": TEAM_SECRET, **overrides}
    return render_chart("-f", str(hosted_values_file(tmp_path, **values)))


def test_hosted_zitadel_serves_the_public_https_issuer(tmp_path: Path):
    """The issuer parts come from the hosted values: the public host, port 443 and HTTPS."""
    env = _zitadel_env(_hosted_docs(tmp_path))

    assert env["ZITADEL_EXTERNALSECURE"]["value"] == "true"
    assert env["ZITADEL_EXTERNALPORT"]["value"] == "443"
    assert env["ZITADEL_EXTERNALDOMAIN"]["value"] == "auth.hosted-test"


def test_hosted_zitadel_sends_mail_through_the_smtp_provider_from_values(tmp_path: Path):
    """The SMTP host, port, login, TLS and sender come from the hosted values."""
    env = _zitadel_env(
        _hosted_docs(
            tmp_path,
            **{
                "zitadel.smtp.host": SMTP_HOST,
                "zitadel.smtp.port": 465,
                "zitadel.smtp.user": "mailer-login",
                "zitadel.smtp.fromAddress": SMTP_FROM,
                "zitadel.smtp.fromName": "Runefoble Friends",
            },
        )
    )

    assert env[f"{ZITADEL_ENV_PREFIX}SMTP_HOST"]["value"] == f"{SMTP_HOST}:465"
    assert env[f"{ZITADEL_ENV_PREFIX}SMTP_USER"]["value"] == "mailer-login"
    assert env[f"{ZITADEL_ENV_PREFIX}TLS"]["value"] == "true"
    assert env[f"{ZITADEL_ENV_PREFIX}FROM"]["value"] == SMTP_FROM
    assert env[f"{ZITADEL_ENV_PREFIX}FROMNAME"]["value"] == "Runefoble Friends"


def test_hosted_smtp_password_is_read_from_the_named_secret(tmp_path: Path):
    """The SMTP password is a secretKeyRef to the operator Secret. It is never a plain value."""
    env = _zitadel_env(_hosted_docs(tmp_path))

    password = env[f"{ZITADEL_ENV_PREFIX}SMTP_PASSWORD"]
    assert "value" not in password
    assert password["valueFrom"]["secretKeyRef"] == {"name": TEAM_SECRET, "key": "smtp-password"}


def test_hosted_zitadel_pod_holds_no_mailpit_reference(tmp_path: Path):
    """A hosted Zitadel pod names no Mailpit host, port or Service."""
    deployment = _doc(_hosted_docs(tmp_path), "Deployment", "zitadel")

    assert "mailpit" not in yaml.safe_dump(deployment).lower()


def test_hosted_bootstrap_job_uses_https_redirects_and_turns_dev_mode_off(tmp_path: Path):
    """The bootstrap Job gets HTTPS redirect URIs, dev mode off and closed registration on."""
    env = _bootstrap_env(_hosted_docs(tmp_path))

    assert env["RUNEFOBLE_ZITADEL_DEV_MODE"]["value"] == "false"
    assert env["RUNEFOBLE_ZITADEL_CLOSED_REGISTRATION"]["value"] == "true"
    redirects = env["RUNEFOBLE_ZITADEL_REDIRECT_URIS"]["value"].split(",")
    logouts = env["RUNEFOBLE_ZITADEL_POST_LOGOUT_URIS"]["value"].split(",")
    assert redirects and logouts
    assert all(uri.startswith("https://") for uri in redirects + logouts)


def test_local_render_keeps_mailpit_smtp_values():
    """The local render keeps the Mailpit SMTP values and the literal empty login."""
    env = _zitadel_env(render_chart())

    assert env[f"{ZITADEL_ENV_PREFIX}SMTP_HOST"]["value"] == "mailpit:1025"
    assert env[f"{ZITADEL_ENV_PREFIX}SMTP_USER"]["value"] == ""
    assert env[f"{ZITADEL_ENV_PREFIX}SMTP_PASSWORD"]["value"] == ""
    assert env[f"{ZITADEL_ENV_PREFIX}TLS"]["value"] == "false"
    assert env[f"{ZITADEL_ENV_PREFIX}FROM"]["value"] == "admin@runefoble.local"
    assert env["ZITADEL_EXTERNALSECURE"]["value"] == "false"


def test_local_bootstrap_job_keeps_open_registration_and_dev_mode():
    """The local Job leaves the login policy alone. Dev mode stays on for http redirects."""
    env = _bootstrap_env(render_chart())

    assert env["RUNEFOBLE_ZITADEL_CLOSED_REGISTRATION"]["value"] == "false"
    assert env["RUNEFOBLE_ZITADEL_DEV_MODE"]["value"] == "true"


@pytest.mark.parametrize(
    ("dotted", "value", "key"),
    [
        ("zitadel.smtp.host", "REPLACE-ME", "zitadel.smtp.host"),
        ("zitadel.smtp.host", "", "zitadel.smtp.host"),
        ("zitadel.smtp.fromAddress", "noreply@runefoble.local", "zitadel.smtp.fromAddress"),
        ("zitadel.smtp.tls", False, "zitadel.smtp.tls"),
        ("zitadel.smtp.user", "REPLACE-ME", "zitadel.smtp.user"),
        ("zitadel.bootstrap.closedRegistration", False, "zitadel.bootstrap.closedRegistration"),
    ],
)
def test_hosted_render_fails_on_an_unsafe_identity_value(
    tmp_path: Path, dotted: str, value: Any, key: str
):
    """A hosted render with an unset SMTP value, plain SMTP, or open registration fails."""
    proc = helm_template_result("-f", str(hosted_values_file(tmp_path, **{dotted: value})))

    assert proc.returncode != 0
    assert key in proc.stderr


def test_hosted_render_fails_when_the_smtp_block_is_missing(tmp_path: Path):
    """A hosted values file with no SMTP block fails the render and names zitadel.smtp.host."""
    values = yaml.safe_load(hosted_values_file(tmp_path).read_text(encoding="utf-8"))
    del values["zitadel"]["smtp"]
    path = tmp_path / "no-smtp.yaml"
    path.write_text(yaml.safe_dump(values, sort_keys=False), encoding="utf-8")

    proc = helm_template_result("-f", str(path))

    assert proc.returncode != 0
    assert "zitadel.smtp.host" in proc.stderr
