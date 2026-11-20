"""Blackbox checks for the hosted network policies (TASK-0962).

The tests render the umbrella chart with `helm template` and check each allow rule against the
consumers lists, the platform paths, and the ingress paths. They read only the rendered manifests.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.helpers.helm import (
    CHART_DIR,
    HOSTED_EXAMPLE,
    helm_template_result,
    hosted_values_file,
    render_chart,
)
from tests.helpers.hosted_workloads import (
    _load,
    _write_values,
)

# Network policies ----------------------------------------------------------------------------

# Pods that send traffic to a platform service without a consumers list naming them. Every other
# ingress source must come from a consumers list.
PLATFORM_CLIENT_SOURCES = {
    "spicedb",
    "zitadel",
    # gateway-mcp verifies tokens against Zitadel (zitadelServiceEnv) but no consumers list names it.
    "gateway-mcp",
    # The backup CronJob dumps PostgreSQL and uploads to the bucket. The restore Job reverses both.
    "postgres-backup",
    "postgres-restore",
    "openpanel",
    "spicedb-schema-migration",
    "zitadel-bootstrap",
    "silo-buckets",
    "grafana",
    "otel-collector",
}


def _kebab(key: str) -> str:
    return re.sub(r"([A-Z])", r"-\1", key).lower()


VALUES = _load(CHART_DIR / "values.yaml")
APP_SERVICES = {
    _kebab(key): svc for key, svc in VALUES["services"].items() if not svc.get("ownTemplate")
}
TARGETS = {_kebab(key): svc for key, svc in VALUES["services"].items() if svc.get("urlEnv")}


def _network_policies(docs: list[dict]) -> dict[str, dict]:
    return {doc["metadata"]["name"]: doc for doc in docs if doc["kind"] == "NetworkPolicy"}


def _peer_app(peer: dict) -> str | None:
    """The app label of a pod peer. None for an IP block or a namespace peer."""
    if "ipBlock" in peer:
        return None
    if "namespaceSelector" in peer:
        return None
    selector = peer.get("podSelector", {})
    if not selector:
        return "ALL"
    return selector.get("matchLabels", {}).get("app")


def _ingress_allows(policies: dict[str, dict]) -> list[tuple[str, str, int]]:
    """(target app, source app, port) for every ingress peer that names a pod."""
    allows = []
    for policy in policies.values():
        target = policy["spec"]["podSelector"].get("matchLabels", {}).get("app")
        for rule in policy["spec"].get("ingress", []):
            for peer in rule.get("from", []):
                source = _peer_app(peer)
                for port in rule.get("ports", []):
                    allows.append((target, source, port["port"]))
    return allows


def _egress_allows(policies: dict[str, dict]) -> list[tuple[str, str, int]]:
    """(source app, target app, port) for every egress peer that names a pod."""
    allows = []
    for policy in policies.values():
        source = policy["spec"]["podSelector"].get("matchLabels", {}).get("app")
        for rule in policy["spec"].get("egress", []):
            for peer in rule.get("to", []):
                target = _peer_app(peer)
                for port in rule.get("ports", []):
                    allows.append((source, target, port["port"]))
    return allows


@pytest.fixture(scope="module")
def hosted_policies(tmp_path_factory: pytest.TempPathFactory) -> list[dict]:
    directory = tmp_path_factory.mktemp("hosted-netpol")
    values = hosted_values_file(
        directory,
        **{"networkPolicy.ingressController.namespace": "ingress-nginx"},
    )
    return render_chart("-f", str(values))


def test_hosted_render_has_default_deny_for_ingress_and_egress(hosted_policies: list[dict]):
    """One default-deny policy selects every release pod, for both directions, and allows nothing."""
    policies = _network_policies(hosted_policies)

    default_deny = policies["default-deny"]

    assert default_deny["spec"]["podSelector"] == {}
    assert set(default_deny["spec"]["policyTypes"]) == {"Ingress", "Egress"}
    assert "ingress" not in default_deny["spec"]
    assert "egress" not in default_deny["spec"]


def test_each_consumer_pair_has_one_ingress_allow_rule(hosted_policies: list[dict]):
    """For every consumers pair, the target accepts one allow from that consumer on its port."""
    allows = _ingress_allows(_network_policies(hosted_policies))

    for target, svc in TARGETS.items():
        for consumer in svc["consumers"]:
            matches = [a for a in allows if a[0] == target and a[1] == consumer]
            assert matches == [(target, consumer, svc["port"])], (target, consumer)


def test_each_consumer_pair_has_one_egress_allow_rule(hosted_policies: list[dict]):
    """For every consumers pair, the consumer may call the target port."""
    allows = _egress_allows(_network_policies(hosted_policies))

    for target, svc in TARGETS.items():
        for consumer in svc["consumers"]:
            matches = [a for a in allows if a[0] == consumer and a[1] == target]
            assert matches == [(consumer, target, svc["port"])], (consumer, target)


def test_no_ingress_allow_names_a_pod_outside_the_documented_sources(hosted_policies: list[dict]):
    """A service target accepts only its consumers. A platform target accepts only its documented clients."""
    allows = _ingress_allows(_network_policies(hosted_policies))

    for target, source, _ in allows:
        if source is None:
            assert target in set(APP_SERVICES) | {"frontend", "swagger-ui", "openpanel", "zitadel"}
        elif source == "ALL":
            assert target == "otel-collector"
        elif target in TARGETS:
            assert source in TARGETS[target]["consumers"], (target, source)
        elif target in {"postgres", "spicedb", "redis", "zitadel", "silo", "loki"}:
            assert source in set(APP_SERVICES) | PLATFORM_CLIENT_SOURCES, (target, source)
        else:
            assert target == "otel-collector", (target, source)


def test_gateway_mcp_accepts_no_ingress_from_any_pod(hosted_policies: list[dict]):
    """gateway-mcp is a ClusterIP endpoint that no consumers list names. No pod may reach it."""
    allows = _ingress_allows(_network_policies(hosted_policies))

    assert [a for a in allows if a[0] == "gateway-mcp"] == []


def test_ingress_controller_reaches_every_routed_service(hosted_policies: list[dict]):
    """Each service on an ingress path accepts the ingress controller on the path port."""
    policies = _network_policies(hosted_policies)
    hosts = _load(HOSTED_EXAMPLE)["ingress"]["hosts"]
    routed = {(path["service"], path["port"]) for host in hosts for path in host["paths"]}

    for service, port in routed:
        policy = policies[f"allow-ingress-{service}"]
        assert policy["spec"]["podSelector"]["matchLabels"] == {"app": service}
        (rule,) = policy["spec"]["ingress"]
        assert rule["ports"] == [{"protocol": "TCP", "port": port}]
        (peer,) = rule["from"]
        assert peer["namespaceSelector"]["matchLabels"] == {
            "kubernetes.io/metadata.name": "ingress-nginx"
        }
        assert peer["podSelector"]["matchLabels"] == {"app.kubernetes.io/name": "traefik"}


def test_every_app_service_reaches_the_platform_it_uses(hosted_policies: list[dict]):
    """Each app service may reach PostgreSQL, SpiceDB, Zitadel, Redis, and Silo when it uses them."""
    egress = _egress_allows(_network_policies(hosted_policies))
    reachable = {(source, target, port) for source, target, port in egress}

    for name, svc in APP_SERVICES.items():
        assert (name, "postgres", 5432) in reachable, name
        assert (name, "spicedb", 50051) in reachable, name
        assert (name, "zitadel", 8080) in reachable, name
        assert (name, "redis", 6379) in reachable, name
        if svc.get("siloEndpoint", True):
            assert (name, "silo", 9000) in reachable, name
        else:
            assert (name, "silo", 9000) not in reachable, name


def test_every_pod_reaches_the_otel_collector_and_dns(hosted_policies: list[dict]):
    """Every release pod sends telemetry to the collector and may query cluster DNS."""
    policies = _network_policies(hosted_policies)

    otel = policies["allow-into-otel-collector"]["spec"]["ingress"][0]
    assert otel["from"] == [{"podSelector": {}}]
    assert {port["port"] for port in otel["ports"]} == {4317, 4318}

    dns = policies["allow-dns-egress"]
    assert dns["spec"]["podSelector"] == {}
    dns_ports = {(p["protocol"], p["port"]) for p in dns["spec"]["egress"][0]["ports"]}
    assert dns_ports == {("UDP", 53), ("TCP", 53)}


def test_external_endpoints_allow_one_address_each(hosted_policies: list[dict]):
    """Each external entry allows egress from its service to one /32 block on its port."""
    policies = _network_policies(hosted_policies)
    expected = {
        "allow-egress-external-0": ("inference-worker", 443),
        "allow-egress-external-1": ("campaign-lore", 443),
        "allow-egress-external-2": ("voice-agent", 443),
        "allow-egress-external-3": ("zitadel", 587),
        "allow-egress-external-4": ("postgres-backup", 443),
        "allow-egress-external-5": ("postgres-restore", 443),
    }

    for name, (source, port) in expected.items():
        policy = policies[name]
        assert policy["spec"]["podSelector"]["matchLabels"] == {"app": source}
        (rule,) = policy["spec"]["egress"]
        assert rule["to"] == [{"ipBlock": {"cidr": "hosted-test/32"}}]
        assert rule["ports"] == [{"protocol": "TCP", "port": port}]


def test_kube_api_egress_covers_the_zitadel_pod_and_bootstrap_job(hosted_policies: list[dict]):
    """The PAT publisher and the bootstrap Job reach the Kubernetes API, and no other pod does."""
    policy = _network_policies(hosted_policies)["allow-egress-kube-api-0"]

    (expression,) = policy["spec"]["podSelector"]["matchExpressions"]
    assert expression["values"] == ["zitadel", "zitadel-bootstrap"]


def test_local_render_has_no_network_policy():
    """The local render has no NetworkPolicy object."""
    docs = render_chart()

    assert [doc for doc in docs if doc["kind"] == "NetworkPolicy"] == []


@pytest.mark.parametrize(
    ("dotted", "key"),
    [
        ("networkPolicy.ingressController.namespace", "networkPolicy.ingressController.namespace"),
    ],
)
def test_hosted_render_fails_without_the_ingress_namespace(tmp_path: Path, dotted: str, key: str):
    """Decision D2d is required. The render fails until the ingress namespace is set."""
    values = _load(hosted_values_file(tmp_path))
    values["networkPolicy"]["ingressController"]["namespace"] = "REPLACE-ME"

    proc = helm_template_result("-f", str(_write_values(tmp_path, values)))

    assert proc.returncode != 0
    assert key in proc.stderr


def test_hosted_render_rejects_a_wide_external_block(tmp_path: Path):
    """An external entry must name one host address. A /24 block fails the render."""
    values = _load(hosted_values_file(tmp_path))
    values["networkPolicy"]["external"][0] = dict(
        values["networkPolicy"]["external"][0], cidr="203.0.113.0/24"
    )

    proc = helm_template_result("-f", str(_write_values(tmp_path, values)))

    assert proc.returncode != 0
    assert "networkPolicy.external[0].cidr" in proc.stderr


@pytest.mark.parametrize("job", ["postgres-backup", "postgres-restore"])
def test_backup_and_restore_jobs_reach_postgres(hosted_policies: list[dict], job: str):
    """The backup and restore pods dump and load PostgreSQL. They reach the database on its port."""
    egress = _egress_allows(_network_policies(hosted_policies))
    inbound = _ingress_allows(_network_policies(hosted_policies))

    assert (job, "postgres", 5432) in egress
    assert ("postgres", job, 5432) in inbound
