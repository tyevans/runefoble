"""Blackbox checks for the hosted values profile and its render guard (TASK-0955).

The tests render the umbrella chart with `helm template`. They read only the example values
file that ships with the chart, and copies of it that a release operator would fill in. They
check exit codes, the key path named in the failure message, and the rendered manifests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.helpers.helm import (
    CHART_DIR,
    HOSTED_EXAMPLE,
    HOSTED_FILL,
    HOSTED_IMAGES,
    HOSTED_PLACEHOLDER,
    helm_template_result,
    hosted_values_file,
    render_chart,
)

VALUES = CHART_DIR / "values.yaml"


def _load(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _del_path(values: dict[str, Any], dotted: str) -> None:
    node = values
    *parents, leaf = dotted.split(".")
    for key in parents:
        node = node[key]
    del node[leaf]


def _string_leaves(node: Any) -> set[str]:
    if isinstance(node, dict):
        return set().union(*(_string_leaves(item) for item in node.values())) if node else set()
    if isinstance(node, list):
        return set().union(*(_string_leaves(item) for item in node)) if node else set()
    if isinstance(node, str):
        return {node}
    return set()


def test_example_as_shipped_fails_on_its_first_placeholder():
    """The shipped profile and image file hold REPLACE-ME. The render fails on a placeholder."""
    proc = helm_template_result("-f", str(HOSTED_EXAMPLE), "-f", str(HOSTED_IMAGES))

    assert proc.returncode != 0
    assert HOSTED_PLACEHOLDER in proc.stderr


def test_filled_example_renders(tmp_path: Path):
    """A copy with every placeholder filled in and no development default renders."""
    docs = render_chart("-f", str(hosted_values_file(tmp_path)))

    kinds = {doc["kind"] for doc in docs}
    assert "Deployment" in kinds


@pytest.mark.parametrize(
    ("dotted", "value", "key"),
    [
        ("global.domain", "runefoble.local", "global.domain"),
        ("zitadel.externalDomain", "localhost", "zitadel.externalDomain"),
        ("mailpit.enabled", True, "mailpit.enabled"),
        ("zitadel.bootstrap.devMode", True, "zitadel.bootstrap.devMode"),
        ("zitadel.externalSecure", False, "zitadel.externalSecure"),
        ("zitadel.bootstrap.patExpirationDate", "2099-01-01T00:00:00Z", "patExpirationDate"),
        ("zitadel.adminEmail", "admin@runefoble.local", "zitadel.adminEmail"),
        (
            "zitadel.bootstrap.redirectUris",
            [f"http://{HOSTED_FILL}/auth/callback"],
            "zitadel.bootstrap.redirectUris",
        ),
        (
            "zitadel.bootstrap.postLogoutRedirectUris",
            ["http://localhost/"],
            "zitadel.bootstrap.postLogoutRedirectUris",
        ),
    ],
)
def test_each_development_default_fails_the_hosted_render(
    tmp_path: Path, dotted: str, value: Any, key: str
):
    """Each development default that reaches a hosted render fails it and names the key."""
    proc = helm_template_result("-f", str(hosted_values_file(tmp_path, **{dotted: value})))

    assert proc.returncode != 0
    assert key in proc.stderr


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_unset_hosted_key_fails_the_render(tmp_path: Path, environment: str):
    """An unset key that the guard reads fails the render. It never takes a development value."""
    values = _load(hosted_values_file(tmp_path))
    values["global"]["environment"] = environment
    _del_path(values, "zitadel.externalSecure")
    path = tmp_path / "unset.yaml"
    path.write_text(yaml.safe_dump(values, sort_keys=False), encoding="utf-8")

    proc = helm_template_result("-f", str(path))

    assert proc.returncode != 0
    assert "zitadel.externalSecure" in proc.stderr


def test_filled_render_holds_no_development_credential_literal(tmp_path: Path):
    """No rendered string equals a long DEV-ONLY credential default from values.yaml.

    The Grafana default `admin` is short and equals the Zitadel username, so a value match
    cannot tell them apart. The chart renders no Secret for the filled copy instead, which
    covers that default. The next test checks that no Secret renders.
    """
    dev_literals = {
        value for value in _string_leaves(_load(VALUES)["credentials"]) if len(value) >= 8
    }
    docs = render_chart("-f", str(hosted_values_file(tmp_path)))

    leaked = _string_leaves(docs) & dev_literals

    assert leaked == set()


def test_filled_render_renders_no_chart_secret(tmp_path: Path):
    """With credentials.existingSecret set, the chart renders no credential Secret."""
    docs = render_chart("-f", str(hosted_values_file(tmp_path)))

    assert [doc["metadata"]["name"] for doc in docs if doc["kind"] == "Secret"] == []
