"""Tests for Helm chart manifests, SpiceDB datastore migrations, and Zitadel configurations."""

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

HELM_CHART = Path("deployments/helm/runefoble")


def _render_helm_templates() -> list[dict]:
    """Render Helm templates into a list of parsed YAML resource manifests."""
    if not shutil.which("helm"):
        pytest.skip("helm CLI not available")

    proc = subprocess.run(
        ["helm", "template", "runefoble", str(HELM_CHART)],
        capture_output=True,
        text=True,
        check=True,
    )
    docs = [doc for doc in yaml.safe_load_all(proc.stdout) if doc]
    return docs


def test_helm_lint():
    """Verify that the Helm chart passes helm lint with zero errors."""
    if not shutil.which("helm"):
        pytest.skip("helm CLI not available")

    proc = subprocess.run(
        ["helm", "lint", str(HELM_CHART)],
        capture_output=True,
        text=True,
    )
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


def test_spicedb_schema_job_datastore_migration_init_container():
    """Verify spicedb-schema-migration hook Job includes datastore migration initContainer."""
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
    init_containers = pod_spec.get("initContainers", [])
    migrate_init = next((c for c in init_containers if c.get("name") == "datastore-migrate"), None)
    assert migrate_init is not None, (
        "datastore-migrate initContainer missing from spicedb-schema-migration Job"
    )
    assert "datastore" in migrate_init.get("args", [])
    assert "migrate" in migrate_init.get("args", [])
    assert "head" in migrate_init.get("args", [])


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
    assert env_map.get("ZITADEL_DATABASE_POSTGRES_HOST") == "postgres"
    assert env_map.get("ZITADEL_DATABASE_POSTGRES_DATABASE") == "zitadel"
    assert "ZITADEL_DATABASE_POSTGRES_ADMIN_USERNAME" in env_map
    assert "ZITADEL_DATABASE_POSTGRES_ADMIN_PASSWORD" in env_map
    assert env_map.get("ZITADEL_DATABASE_POSTGRES_ADMIN_SSL_MODE") == "disable"
    assert "ZITADEL_DATABASE_POSTGRES_USER_USERNAME" in env_map
    assert "ZITADEL_DATABASE_POSTGRES_USER_PASSWORD" in env_map
    assert env_map.get("ZITADEL_DATABASE_POSTGRES_USER_SSL_MODE") == "disable"
    assert env_map.get("ZITADEL_FIRSTINSTANCE_ORG_HUMAN_USERNAME") == "admin"
    assert env_map.get("ZITADEL_FIRSTINSTANCE_ORG_HUMAN_EMAIL") == "admin@runefoble.local"
    assert "ZITADEL_FIRSTINSTANCE_ORG_HUMAN_PASSWORD" in env_map


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
    env_map = {item["name"]: item["value"] for item in container.get("env", [])}

    assert env_map.get("ZITADEL_DEFAULTINSTANCE_SMTPCONFIGURATION_SMTP_HOST") == "mailpit:1025"
    assert env_map.get("ZITADEL_DEFAULTINSTANCE_SMTPCONFIGURATION_SMTP_TLS") == "false"
    assert env_map.get("ZITADEL_DEFAULTINSTANCE_SMTPCONFIGURATION_SMTP_SSL") == "false"
    assert (
        env_map.get("ZITADEL_DEFAULTINSTANCE_SMTPCONFIGURATION_SMTP_FROM")
        == "admin@runefoble.local"
    )
    assert env_map.get("ZITADEL_DEFAULTINSTANCE_SMTPCONFIGURATION_SMTP_FROMNAME") == "Runefoble"


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
        paths = {
            p["path"]: p["backend"]["service"]["name"]
            for p in rule.get("http", {}).get("paths", [])
        }
        assert "/mail" in paths, f"Missing /mail route on host {host}"
        assert paths["/mail"] == "mailpit"
        assert "/mailpit" in paths, f"Missing /mailpit route on host {host}"
        assert paths["/mailpit"] == "mailpit"
