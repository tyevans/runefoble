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
