"""Helpers for the hosted render tests (TASK-0962). They read the rendered manifests only."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

WORKLOAD_KINDS = ("Deployment", "StatefulSet", "Job", "CronJob")


def _load(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _del_path(values: dict[str, Any], dotted: str) -> None:
    """Delete one key. Each node on the path is copied first, because YAML anchors share dicts."""
    node = values
    *parents, leaf = dotted.split(".")
    for key in parents:
        node[key] = dict(node[key])
        node = node[key]
    del node[leaf]


def _write_values(tmp_path: Path, values: dict[str, Any]) -> Path:
    path = tmp_path / "hosted-hardening.yaml"
    path.write_text(yaml.safe_dump(values, sort_keys=False), encoding="utf-8")
    return path


def _containers(docs: list[dict]) -> list[tuple[dict, dict]]:
    """Every container and init container of every workload, with the workload document."""
    found: list[tuple[dict, dict]] = []
    for doc in docs:
        if doc["kind"] not in WORKLOAD_KINDS:
            continue
        if doc["kind"] == "CronJob":
            spec = doc["spec"]["jobTemplate"]["spec"]["template"]["spec"]
        else:
            spec = doc["spec"]["template"]["spec"]
        for container in (spec.get("initContainers") or []) + spec["containers"]:
            found.append((doc, container))
    return found


def _pod_spec(doc: dict) -> dict:
    if doc["kind"] == "CronJob":
        return doc["spec"]["jobTemplate"]["spec"]["template"]["spec"]
    return doc["spec"]["template"]["spec"]


def _label(doc: dict, container: dict) -> str:
    return f"{doc['kind']}/{doc['metadata']['name']}/{container['name']}"
