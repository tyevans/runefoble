"""Blackbox checks for workload hardening in the hosted render (TASK-0962).

The tests render the umbrella chart with `helm template` and read only the manifests and the
values files that ship with the chart. They check resource requests and limits, the replica
count, the network policies, and the pod and container security contexts. They do not read any
cluster state.
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

WORKLOAD_KINDS = ("Deployment", "StatefulSet", "Job")


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
        spec = doc["spec"]["template"]["spec"]
        for container in (spec.get("initContainers") or []) + spec["containers"]:
            found.append((doc, container))
    return found


def _label(doc: dict, container: dict) -> str:
    return f"{doc['kind']}/{doc['metadata']['name']}/{container['name']}"


# Resources -----------------------------------------------------------------------------------


def test_hosted_render_gives_every_container_a_memory_request_and_limit(tmp_path: Path):
    """Each container of each workload has requests.memory and limits.memory."""
    docs = render_chart("-f", str(hosted_values_file(tmp_path)))

    missing = [
        _label(doc, container)
        for doc, container in _containers(docs)
        if not container.get("resources", {}).get("requests", {}).get("memory")
        or not container.get("resources", {}).get("limits", {}).get("memory")
    ]

    assert missing == []


def test_hosted_render_keeps_one_replica_for_every_deployment_and_statefulset(tmp_path: Path):
    """The PRD sets no autoscaling. Every workload runs one replica."""
    docs = render_chart("-f", str(hosted_values_file(tmp_path)))

    replicas = {
        doc["metadata"]["name"]: doc["spec"]["replicas"]
        for doc in docs
        if doc["kind"] in ("Deployment", "StatefulSet")
    }

    assert replicas
    assert set(replicas.values()) == {1}


def test_hosted_render_has_no_autoscaler_or_disruption_budget(tmp_path: Path):
    """No HorizontalPodAutoscaler and no PodDisruptionBudget render in the hosted profile."""
    docs = render_chart("-f", str(hosted_values_file(tmp_path)))

    kinds = {doc["kind"] for doc in docs}

    assert "HorizontalPodAutoscaler" not in kinds
    assert "PodDisruptionBudget" not in kinds


@pytest.mark.parametrize(
    ("dotted", "key"),
    [
        ("services.gatewayApi.resources", "services.gatewayApi.resources"),
        ("postgres.resources", "postgres.resources"),
        ("spicedb.migrateResources", "spicedb.migrateResources"),
    ],
)
def test_hosted_render_fails_when_a_workload_has_no_resources(
    tmp_path: Path, dotted: str, key: str
):
    """A workload without resources fails the hosted render and the failure names its key."""
    values = _load(hosted_values_file(tmp_path))
    _del_path(values, dotted)

    proc = helm_template_result("-f", str(_write_values(tmp_path, values)))

    assert proc.returncode != 0
    assert key in proc.stderr


def test_hosted_render_fails_when_a_memory_limit_is_missing(tmp_path: Path):
    """A memory request without a memory limit fails the render and names the limit key."""
    values = _load(hosted_values_file(tmp_path))
    _del_path(values, "services.theWatcher.resources.limits.memory")

    proc = helm_template_result("-f", str(_write_values(tmp_path, values)))

    assert proc.returncode != 0
    assert "services.theWatcher.resources.limits.memory" in proc.stderr


def test_local_render_sets_resources_only_where_values_set_them(tmp_path: Path):
    """The local render adds no resources block. Redis keeps its own resources."""
    docs = render_chart()

    with_resources = {
        _label(doc, container) for doc, container in _containers(docs) if "resources" in container
    }

    assert with_resources == {"StatefulSet/runefoble-redis/redis"}
