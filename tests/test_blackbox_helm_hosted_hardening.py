"""Blackbox checks for workload resources and pod security in the hosted render (TASK-0962).

The tests render the umbrella chart with `helm template` and read only the manifests and the
values files that ship with the chart. They check resource requests and limits, the replica
count, and the pod and container security contexts. They do not read any cluster state.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.helpers.helm import (
    CHART_DIR,
    helm_template_result,
    hosted_values_file,
    render_chart,
)
from tests.helpers.hosted_workloads import (
    WORKLOAD_KINDS,
    _containers,
    _del_path,
    _label,
    _load,
    _pod_spec,
    _write_values,
)

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


# Pod security -------------------------------------------------------------------------------

PROFILE_PAGE = CHART_DIR.parents[2] / "docs" / "reference" / "hosted-profile.md"


def _exception_containers() -> set[str]:
    """Container names in the Security exceptions table of the hosted profile page."""
    text = PROFILE_PAGE.read_text(encoding="utf-8")
    section = text.split("## Security exceptions", 1)[1].split("\n## ", 1)[0]
    names = set()
    for line in section.splitlines():
        match = re.match(r"^\|\s*`([^`]+)`\s*\|", line)
        if match:
            names.add(match.group(1))
    return names


@pytest.fixture(scope="module")
def hosted_workloads(tmp_path_factory: pytest.TempPathFactory) -> list[tuple[dict, dict]]:
    directory = tmp_path_factory.mktemp("hosted-security")
    values = hosted_values_file(
        directory, **{"networkPolicy.ingressController.namespace": "ingress-nginx"}
    )
    return _containers(render_chart("-f", str(values)))


def test_hosted_render_sets_seccomp_on_every_pod(hosted_workloads: list[tuple[dict, dict]]):
    """Every pod runs with the RuntimeDefault seccomp profile."""
    pods = {(doc["kind"], doc["metadata"]["name"]): _pod_spec(doc) for doc, _ in hosted_workloads}

    profiles = {
        key: spec.get("securityContext", {}).get("seccompProfile", {}).get("type")
        for key, spec in pods.items()
    }

    assert set(profiles.values()) == {"RuntimeDefault"}, profiles


def test_hosted_render_blocks_privilege_escalation_for_every_container(
    hosted_workloads: list[tuple[dict, dict]],
):
    """No container may gain privileges beyond its parent."""
    missing = [
        _label(doc, c)
        for doc, c in hosted_workloads
        if c.get("securityContext", {}).get("allowPrivilegeEscalation") is not False
    ]

    assert missing == []


def test_hosted_render_runs_application_containers_as_non_root_read_only(
    hosted_workloads: list[tuple[dict, dict]],
):
    """Every container outside the documented exceptions drops all capabilities and runs as non-root."""
    exceptions = _exception_containers()
    application = [(doc, c) for doc, c in hosted_workloads if c["name"] not in exceptions]

    assert application
    for doc, container in application:
        sc = container.get("securityContext", {})
        assert sc.get("runAsNonRoot") is True, _label(doc, container)
        assert isinstance(sc.get("runAsUser"), int) and sc["runAsUser"] > 0, _label(doc, container)
        assert sc.get("capabilities", {}).get("drop") == ["ALL"], _label(doc, container)
        assert sc.get("readOnlyRootFilesystem") is True, _label(doc, container)
        mounts = {m["mountPath"] for m in container.get("volumeMounts", [])}
        assert "/tmp" in mounts, _label(doc, container)


def test_security_exceptions_match_the_profile_page(
    hosted_workloads: list[tuple[dict, dict]], restore_workloads: list[tuple[dict, dict]]
):
    """A container without runAsNonRoot is listed in the profile page, and each listed container exists.

    The restore Job renders only when restore is on, so the check reads both renders.
    """
    everything = hosted_workloads + restore_workloads
    rendered = {c["name"] for _, c in everything}
    without_non_root = {
        c["name"]
        for _, c in everything
        if c.get("securityContext", {}).get("runAsNonRoot") is not True
    }

    assert without_non_root == _exception_containers()
    assert _exception_containers() <= rendered


def test_local_render_sets_no_hosted_security_context():
    """The local render has no seccomp profile and no pod or container security context added."""
    docs = render_chart()

    rendered = [doc for doc in docs if doc["kind"] in WORKLOAD_KINDS]
    seccomp = [
        doc["metadata"]["name"]
        for doc in rendered
        if _pod_spec(doc).get("securityContext", {}).get("seccompProfile")
    ]

    assert seccomp == []


@pytest.fixture(scope="module")
def restore_workloads(tmp_path_factory: pytest.TempPathFactory) -> list[tuple[dict, dict]]:
    """The hosted render with the one-time restore Job turned on (TASK-0961)."""
    directory = tmp_path_factory.mktemp("hosted-restore")
    values = hosted_values_file(
        directory,
        **{
            "networkPolicy.ingressController.namespace": "ingress-nginx",
            "restore.enabled": True,
            "restore.objectPrefix": "postgres/2026-11-18",
        },
    )
    return _containers(render_chart("-f", str(values)))


def test_restore_job_containers_are_hardened_when_restore_is_on(
    restore_workloads: list[tuple[dict, dict]],
):
    """The restore Job carries resources, seccomp, and the third-party container settings."""
    restore = [
        (doc, c) for doc, c in restore_workloads if doc["metadata"]["name"] == "postgres-restore"
    ]

    assert {c["name"] for _, c in restore} == {"download", "restore"}
    for doc, container in restore:
        assert container["resources"]["requests"]["memory"], _label(doc, container)
        assert container["resources"]["limits"]["memory"], _label(doc, container)
        assert container["securityContext"]["allowPrivilegeEscalation"] is False
        assert _pod_spec(doc)["securityContext"]["seccompProfile"]["type"] == "RuntimeDefault"
