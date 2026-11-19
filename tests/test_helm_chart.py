"""Tests for Helm chart manifests, SpiceDB datastore migrations, and Zitadel configurations."""

from pathlib import Path

from tests.helpers.helm import render_chart, require_helm
from tests.helpers.process import run_command

HELM_CHART = Path("deployments/helm/runefoble")


def _render_helm_templates() -> list[dict]:
    """Render Helm templates into a list of parsed YAML resource manifests."""
    return render_chart()


def test_helm_lint():
    """Verify that the Helm chart passes helm lint with zero errors."""
    require_helm()

    proc = run_command(["helm", "lint", str(HELM_CHART)], timeout=240.0)
    assert proc.returncode == 0, f"helm lint failed:\n{proc.stdout}\n{proc.stderr}"
    assert "0 chart(s) failed" in proc.stdout


def test_spicedb_deployment_datastore_migration_init_container():
    """Verify SpiceDB deployment includes datastore migration initContainer."""
    docs = _render_helm_templates()
    spicedb_deploy = next(
        (
            d
            for d in docs
            if d.get("kind") == "Deployment" and d.get("metadata", {}).get("name") == "spicedb"
        ),
        None,
    )
    assert spicedb_deploy is not None, "spicedb Deployment manifest not found"

    pod_spec = spicedb_deploy["spec"]["template"]["spec"]
    init_containers = pod_spec.get("initContainers", [])
    migrate_init = next((c for c in init_containers if c.get("name") == "spicedb-migrate"), None)
    assert migrate_init is not None, "spicedb-migrate initContainer missing from spicedb Deployment"
    assert "datastore" in migrate_init.get("args", [])
    assert "migrate" in migrate_init.get("args", [])
    assert "head" in migrate_init.get("args", [])


def test_spicedb_schema_job_does_not_migrate_the_datastore_concurrently():
    """The Deployment owns the datastore migration. The hook Job must not run a second one."""
    docs = _render_helm_templates()
    schema_job = next(
        (
            d
            for d in docs
            if d.get("kind") == "Job"
            and d.get("metadata", {}).get("name") == "spicedb-schema-migration"
        ),
        None,
    )
    assert schema_job is not None, "spicedb-schema-migration Job manifest not found"

    annotations = schema_job["metadata"].get("annotations", {})
    assert "post-install,post-upgrade" in annotations.get("helm.sh/hook", "")

    pod_spec = schema_job["spec"]["template"]["spec"]
    assert not pod_spec.get("initContainers"), "schema Job must not run a migration initContainer"
    assert pod_spec["containers"][0]["command"][:2] == ["zed", "schema"]


def test_zitadel_deployment_postgres_credentials_and_ssl_mode():
    """Verify Zitadel deployment configures Postgres admin/user credentials and disabled SSL."""
    docs = _render_helm_templates()
    zitadel_deploy = next(
        (
            d
            for d in docs
            if d.get("kind") == "Deployment" and d.get("metadata", {}).get("name") == "zitadel"
        ),
        None,
    )
    assert zitadel_deploy is not None, "zitadel Deployment manifest not found"

    container = zitadel_deploy["spec"]["template"]["spec"]["containers"][0]
    args = container.get("args", [])
    assert "--tlsMode" in args
    assert "disabled" in args

    env_map = {
        item["name"]: item["value"]
        for item in container.get("env", [])
        if "name" in item and "value" in item
    }
    secret_refs = {
        item["name"]: item["valueFrom"]["secretKeyRef"]
        for item in container.get("env", [])
        if "secretKeyRef" in item.get("valueFrom", {})
    }
    assert env_map.get("ZITADEL_DATABASE_POSTGRES_HOST") == "postgres"
    assert env_map.get("ZITADEL_DATABASE_POSTGRES_DATABASE") == "zitadel"
    assert "ZITADEL_DATABASE_POSTGRES_ADMIN_USERNAME" in env_map
    assert secret_refs.get("ZITADEL_DATABASE_POSTGRES_ADMIN_PASSWORD") == {
        "name": "runefoble-credentials",
        "key": "postgres-password",
    }
    assert env_map.get("ZITADEL_DATABASE_POSTGRES_ADMIN_SSL_MODE") == "disable"
    assert "ZITADEL_DATABASE_POSTGRES_USER_USERNAME" in env_map
    assert secret_refs.get("ZITADEL_DATABASE_POSTGRES_USER_PASSWORD") == {
        "name": "runefoble-credentials",
        "key": "postgres-password",
    }
    assert env_map.get("ZITADEL_DATABASE_POSTGRES_USER_SSL_MODE") == "disable"
    assert env_map.get("ZITADEL_FIRSTINSTANCE_ORG_HUMAN_USERNAME") == "admin"
    assert env_map.get("ZITADEL_FIRSTINSTANCE_ORG_HUMAN_EMAIL") == "admin@runefoble.local"
    assert secret_refs.get("ZITADEL_FIRSTINSTANCE_ORG_HUMAN_PASSWORD") == {
        "name": "runefoble-credentials",
        "key": "zitadel-admin-password",
    }


def test_mailpit_deployment_and_service():
    """Verify Mailpit deployment and service manifests for email testing and mock SMTP."""
    docs = _render_helm_templates()
    mailpit_deploy = next(
        (
            d
            for d in docs
            if d.get("kind") == "Deployment" and d.get("metadata", {}).get("name") == "mailpit"
        ),
        None,
    )
    assert mailpit_deploy is not None, "mailpit Deployment manifest not found"

    container = mailpit_deploy["spec"]["template"]["spec"]["containers"][0]
    assert "mailpit" in container["image"]

    ports = {p.get("name"): p.get("containerPort") for p in container.get("ports", [])}
    assert ports.get("smtp") == 1025
    assert ports.get("http") == 8025

    env_map = {item["name"]: item["value"] for item in container.get("env", [])}
    assert env_map.get("MP_WEBROOT") == "/mail/"
    assert env_map.get("MP_SMTP_AUTH_ACCEPT_ANY") == "true"

    mailpit_svc = next(
        (
            d
            for d in docs
            if d.get("kind") == "Service" and d.get("metadata", {}).get("name") == "mailpit"
        ),
        None,
    )
    assert mailpit_svc is not None, "mailpit Service manifest not found"
    svc_ports = {p.get("name"): p.get("port") for p in mailpit_svc["spec"]["ports"]}
    assert svc_ports.get("smtp") == 1025
    assert svc_ports.get("http") == 8025


def test_zitadel_deployment_mailpit_smtp_configuration():
    """Verify Zitadel deployment wires SMTP to Mailpit for local email testing."""
    docs = _render_helm_templates()
    zitadel_deploy = next(
        (
            d
            for d in docs
            if d.get("kind") == "Deployment" and d.get("metadata", {}).get("name") == "zitadel"
        ),
        None,
    )
    assert zitadel_deploy is not None

    container = zitadel_deploy["spec"]["template"]["spec"]["containers"][0]
    env_map = {item["name"]: item.get("value") for item in container.get("env", [])}

    assert env_map.get("ZITADEL_DEFAULTINSTANCE_SMTPCONFIGURATION_SMTP_HOST") == "mailpit:1025"
    assert env_map.get("ZITADEL_DEFAULTINSTANCE_SMTPCONFIGURATION_TLS") == "false"
    assert env_map.get("ZITADEL_DEFAULTINSTANCE_SMTPCONFIGURATION_FROM") == "admin@runefoble.local"
    assert env_map.get("ZITADEL_DEFAULTINSTANCE_SMTPCONFIGURATION_FROMNAME") == "Runefoble"
    assert (
        env_map.get("ZITADEL_DEFAULTINSTANCE_DOMAINPOLICY_SMTPSENDERADDRESSMATCHESINSTANCEDOMAIN")
        == "false"
    )


def test_ingress_mailpit_routing():
    """Verify Ingress rules route /mail and /mailpit to the Mailpit service."""
    docs = _render_helm_templates()
    ingress = next(
        (d for d in docs if d.get("kind") == "Ingress" and "mailpit" in str(d)),
        None,
    )
    assert ingress is not None, "Ingress manifest with mailpit routes not found"

    for rule in ingress["spec"]["rules"]:
        host = rule.get("host")
        if host == "auth.localhost":
            # The Zitadel host serves only Zitadel.
            continue
        paths = {
            p["path"]: p["backend"]["service"]["name"]
            for p in rule.get("http", {}).get("paths", [])
        }
        assert "/mail" in paths, f"Missing /mail route on host {host}"
        assert paths["/mail"] == "mailpit"
        assert "/mailpit" in paths, f"Missing /mailpit route on host {host}"
        assert paths["/mailpit"] == "mailpit"


def test_ingress_routes_healthz_to_gateway_api():
    """A request to /healthz on the app hosts reaches the gateway health report, not the frontend."""
    docs = _render_helm_templates()
    ingress = next(
        (d for d in docs if d.get("kind") == "Ingress" and "mailpit" in str(d)),
        None,
    )
    assert ingress is not None, "Ingress manifest not found"

    app_hosts = [r for r in ingress["spec"]["rules"] if r.get("host") != "auth.localhost"]
    assert app_hosts, "no app host in the Ingress"
    for rule in app_hosts:
        paths = {
            p["path"]: p["backend"]["service"]["name"]
            for p in rule.get("http", {}).get("paths", [])
        }
        assert paths.get("/healthz") == "gateway-api", f"/healthz not routed on {rule['host']}"


def test_local_render_creates_the_campaign_lore_embedding_secret():
    """campaign-lore reads its embedding key from a Secret. The local install must create it."""
    docs = _render_helm_templates()
    secret = next(
        (
            d
            for d in docs
            if d.get("kind") == "Secret"
            and d.get("metadata", {}).get("name") == "campaign-lore-embedding"
        ),
        None,
    )
    assert secret is not None, "campaign-lore-embedding Secret not rendered for the local install"
    assert "api-key" in secret.get("stringData", {})


def test_gateway_mcp_reads_the_spicedb_preshared_key():
    """gateway-mcp fails at start-up without RUNEFOBLE_SPICEDB_PRESHARED_KEY."""
    docs = _render_helm_templates()
    deploy = next(
        (
            d
            for d in docs
            if d.get("kind") == "Deployment" and d.get("metadata", {}).get("name") == "gateway-mcp"
        ),
        None,
    )
    assert deploy is not None, "gateway-mcp Deployment not found"
    env = deploy["spec"]["template"]["spec"]["containers"][0]["env"]
    entry = next(e for e in env if e["name"] == "RUNEFOBLE_SPICEDB_PRESHARED_KEY")
    assert entry["valueFrom"]["secretKeyRef"]["key"] == "spicedb-preshared-key"


def test_postgres_allows_enough_connections_for_every_service():
    """About 17 clients each hold a pool. The server default of 100 refuses the last ones."""
    docs = _render_helm_templates()
    deploy = next(
        (
            d
            for d in docs
            if d.get("kind") == "StatefulSet" and d.get("metadata", {}).get("name") == "postgres"
        ),
        None,
    )
    assert deploy is not None, "postgres StatefulSet not found"
    args = deploy["spec"]["template"]["spec"]["containers"][0]["args"]
    limit = int(next(a for a in args if a.startswith("max_connections=")).split("=")[1])
    assert limit >= 200
