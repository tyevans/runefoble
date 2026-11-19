"""Chart render tests for the stateful platform services (TASK-0881).

PostgreSQL, Silo and Redis keep their data on a PersistentVolumeClaim. A pod restart keeps the
data. Governed by ADR-0005 (Helm and Kind) and ADR-0011 (event sourcing needs durable storage).
"""

from __future__ import annotations

from tests.helpers.helm import render_chart


def _find(docs: list[dict], kind: str, name: str) -> dict:
    found = [d for d in docs if d.get("kind") == kind and d["metadata"]["name"] == name]
    assert len(found) == 1, f"expected one {kind} named {name}, found {len(found)}"
    return found[0]


def _data_claim(statefulset: dict) -> dict:
    claims = statefulset["spec"]["volumeClaimTemplates"]
    assert len(claims) == 1, "a stateful service needs exactly one data claim"
    return claims[0]


def _mount_path(statefulset: dict, claim_name: str) -> str:
    container = statefulset["spec"]["template"]["spec"]["containers"][0]
    mounts = [m["mountPath"] for m in container.get("volumeMounts", []) if m["name"] == claim_name]
    assert len(mounts) == 1, f"container does not mount the {claim_name} claim"
    return mounts[0]


def test_postgres_is_a_statefulset_with_a_data_claim() -> None:
    docs = render_chart()

    statefulset = _find(docs, "StatefulSet", "postgres")
    assert not [
        d for d in docs if d.get("kind") == "Deployment" and d["metadata"]["name"] == "postgres"
    ]

    claim = _data_claim(statefulset)
    assert claim["metadata"]["name"] == "data"
    assert claim["spec"]["resources"]["requests"]["storage"] == "5Gi"
    assert claim["spec"]["accessModes"] == ["ReadWriteOnce"]

    assert _mount_path(statefulset, "data") == "/var/lib/postgresql/data"
    container = statefulset["spec"]["template"]["spec"]["containers"][0]
    env = {item["name"]: item.get("value") for item in container["env"]}
    assert env["PGDATA"] == "/var/lib/postgresql/data/pgdata"


def test_postgres_claim_size_and_storage_class_follow_values() -> None:
    docs = render_chart(
        "--set",
        "postgres.persistence.size=20Gi",
        "--set",
        "postgres.persistence.storageClass=fast-ssd",
    )

    claim = _data_claim(_find(docs, "StatefulSet", "postgres"))
    assert claim["spec"]["resources"]["requests"]["storage"] == "20Gi"
    assert claim["spec"]["storageClassName"] == "fast-ssd"


def test_empty_storage_class_leaves_the_cluster_default_in_place() -> None:
    docs = render_chart()

    claim = _data_claim(_find(docs, "StatefulSet", "postgres"))
    assert "storageClassName" not in claim["spec"]


def test_silo_is_a_statefulset_whose_data_claim_backs_the_object_store() -> None:
    docs = render_chart()

    statefulset = _find(docs, "StatefulSet", "silo")
    assert not [
        d for d in docs if d.get("kind") == "Deployment" and d["metadata"]["name"] == "silo"
    ]

    claim = _data_claim(statefulset)
    assert claim["spec"]["resources"]["requests"]["storage"] == "10Gi"
    assert _mount_path(statefulset, "data") == "/data"

    args = statefulset["spec"]["template"]["spec"]["containers"][0]["args"]
    assert args[:2] == ["server", "/data"]


def test_redis_is_a_statefulset_with_append_only_file_on_a_data_claim() -> None:
    docs = render_chart()

    statefulset = _find(docs, "StatefulSet", "runefoble-redis")
    assert not [
        d
        for d in docs
        if d.get("kind") == "Deployment" and d["metadata"]["name"] == "runefoble-redis"
    ]

    claim = _data_claim(statefulset)
    assert claim["spec"]["resources"]["requests"]["storage"] == "1Gi"
    assert _mount_path(statefulset, "data") == "/data"

    args = statefulset["spec"]["template"]["spec"]["containers"][0]["args"]
    assert args == ["redis-server", "--appendonly", "yes"]


def test_stateful_services_keep_their_service_names_and_selectors() -> None:
    docs = render_chart()

    for name in ("postgres", "silo", "runefoble-redis"):
        statefulset = _find(docs, "StatefulSet", name)
        service = _find(docs, "Service", name)
        pod_labels = statefulset["spec"]["template"]["metadata"]["labels"]
        assert statefulset["spec"]["serviceName"] == name
        for key, value in service["spec"]["selector"].items():
            assert pod_labels.get(key) == value, f"{name} Service selector misses its pods"
