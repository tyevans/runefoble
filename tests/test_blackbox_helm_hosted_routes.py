"""Blackbox checks for the development-only public routes in the hosted profile (TASK-0957).

The tests render the umbrella chart with `helm template`. They read only the hosted example
values file and copies of it that a release operator would fill in, plus the default render.
They check exit codes, the path or key named in the failure message, and the rendered manifests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from tests.helpers.helm import (
    helm_template_result,
    hosted_values_file,
    render_chart,
)

DEV_PREFIXES = ("/mail", "/mailpit", "/docs", "/swagger-ui", "/analytics")
DEV_WORKLOADS = ("mailpit", "swagger-ui", "openpanel")


def _ingress_paths(docs: list[dict]) -> list[dict]:
    """Return every Ingress path entry from the rendered documents, with its host."""
    entries: list[dict] = []
    for doc in docs:
        if doc.get("kind") != "Ingress":
            continue
        for rule in doc["spec"].get("rules", []):
            for path in rule["http"]["paths"]:
                entries.append({"host": rule["host"], **path})
    return entries


def _path_has_prefix(path: str, prefix: str) -> bool:
    """Match an Ingress Prefix path: equal to the prefix, or below it on a slash boundary."""
    return path == prefix or path.startswith(prefix.rstrip("/") + "/")


def _write_variant(directory: Path, edit: Any) -> Path:
    """Write a filled hosted copy, after `edit` changes its parsed values."""
    values = yaml.safe_load(hosted_values_file(directory).read_text(encoding="utf-8"))
    edit(values)
    path = directory / "variant.yaml"
    path.write_text(yaml.safe_dump(values, sort_keys=False), encoding="utf-8")
    return path


def test_filled_hosted_render_serves_no_development_prefix(tmp_path: Path):
    """No Ingress path in a hosted render has a development prefix."""
    docs = render_chart("-f", str(hosted_values_file(tmp_path)))

    leaked = [
        entry["path"]
        for entry in _ingress_paths(docs)
        if any(_path_has_prefix(entry["path"], prefix) for prefix in DEV_PREFIXES)
    ]

    assert leaked == []


def test_filled_hosted_render_targets_no_development_workload(tmp_path: Path):
    """No Ingress path in a hosted render targets mailpit, swagger-ui or openpanel."""
    docs = render_chart("-f", str(hosted_values_file(tmp_path)))

    targeted = [
        entry["path"]
        for entry in _ingress_paths(docs)
        if entry["backend"]["service"]["name"] in DEV_WORKLOADS
    ]

    assert targeted == []


def test_filled_hosted_render_renders_no_development_workload(tmp_path: Path):
    """No Deployment or Service named mailpit, swagger-ui or openpanel renders in a hosted render."""
    docs = render_chart("-f", str(hosted_values_file(tmp_path)))

    rendered = [
        doc["metadata"]["name"]
        for doc in docs
        if doc["kind"] in ("Deployment", "Service") and doc["metadata"]["name"] in DEV_WORKLOADS
    ]

    assert rendered == []


def test_hosted_guard_rejects_mail_path_when_mailpit_is_off(tmp_path: Path):
    """A /mail path fails the hosted render and the message names the path."""

    def add_mail_path(values: dict) -> None:
        values["ingress"]["hosts"][0]["paths"].append(
            {"path": "/mail", "pathType": "Prefix", "service": "mailpit", "port": 8025}
        )

    proc = helm_template_result("-f", str(_write_variant(tmp_path, add_mail_path)))

    assert proc.returncode != 0
    assert "/mail" in proc.stderr


def test_hosted_guard_rejects_hosted_mailpit_with_mail_path(tmp_path: Path):
    """Mailpit on plus a /mail path fails the hosted render. The mailpit.enabled check fails it."""

    def enable_mailpit_with_mail_path(values: dict) -> None:
        values["mailpit"]["enabled"] = True
        values["ingress"]["hosts"][0]["paths"].append(
            {"path": "/mail", "pathType": "Prefix", "service": "mailpit", "port": 8025}
        )

    proc = helm_template_result("-f", str(_write_variant(tmp_path, enable_mailpit_with_mail_path)))

    assert proc.returncode != 0
    assert "mailpit.enabled" in proc.stderr or "/mail" in proc.stderr


def test_hosted_guard_rejects_dev_prefix_path_when_workload_is_disabled(tmp_path: Path):
    """A /docs path fails the hosted render even when the Swagger UI workload is off."""

    def add_docs_path(values: dict) -> None:
        values["swaggerUI"]["enabled"] = False
        values["ingress"]["hosts"][0]["paths"].append(
            {"path": "/docs", "pathType": "Prefix", "service": "swagger-ui", "port": 8080}
        )

    proc = helm_template_result("-f", str(_write_variant(tmp_path, add_docs_path)))

    assert proc.returncode != 0
    assert "/docs" in proc.stderr


def test_hosted_guard_rejects_route_to_disabled_workload(tmp_path: Path):
    """A path with an ordinary prefix that targets a disabled workload fails the render."""

    def add_viewer_path(values: dict) -> None:
        values["openpanel"]["enabled"] = False
        values["ingress"]["hosts"][0]["paths"].append(
            {"path": "/viewer", "pathType": "Prefix", "service": "openpanel", "port": 3000}
        )

    proc = helm_template_result("-f", str(_write_variant(tmp_path, add_viewer_path)))

    assert proc.returncode != 0
    assert "/viewer" in proc.stderr
    assert "openpanel" in proc.stderr


def test_local_default_render_keeps_mailpit_and_swagger_routes():
    """The Kind render still routes /mail and /docs to the development workloads."""
    docs = render_chart()

    paths = {(entry["path"], entry["backend"]["service"]["name"]) for entry in _ingress_paths(docs)}
    rendered = {doc["metadata"]["name"] for doc in docs if doc["kind"] == "Deployment"}

    assert ("/mail", "mailpit") in paths
    assert ("/docs", "swagger-ui") in paths
    assert {"mailpit", "swagger-ui"} <= rendered
