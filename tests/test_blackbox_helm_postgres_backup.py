"""Blackbox checks for the PostgreSQL backup CronJob, the restore Job, and their hosted guard (TASK-0961).

The tests render the umbrella chart with `helm template` and read only the manifests and the exit
code. They check the schedule, the endpoint, the credential source, the restore switch, the
encryption switch, and the hosted guard failures. The live restore is in
`tests/test_blackbox_postgres_backup_restore.py`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from tests.helpers.helm import (
    HOSTED_EXAMPLE,
    helm_template_result,
    hosted_values_file,
    render_chart,
)

BACKUP_NAME = "postgres-backup"
RESTORE_NAME = "postgres-restore"
SECRET_NAME = "runefoble-backup-credentials"
DEFAULT_SCHEDULE = "17 2 * * *"
EXAMPLE_IMAGE = yaml.safe_load(HOSTED_EXAMPLE.read_text(encoding="utf-8"))["backup"]["image"]
LOCAL_BACKUP_ARGS = [
    "--set",
    "backup.enabled=true",
    "--set",
    "backup.endpoint=http://silo:9000",
    "--set",
    "backup.bucket=runefoble-backups",
    "--set",
    f"backup.credentialsSecret={SECRET_NAME}",
    "--set",
    f"backup.image={EXAMPLE_IMAGE}",
]
RESTORE_ARGS = [
    "--set",
    "restore.enabled=true",
    "--set",
    "restore.objectPrefix=postgres/2026-11-18",
]


def _named(docs: list[dict[str, Any]], kind: str, name: str) -> list[dict[str, Any]]:
    return [doc for doc in docs if doc.get("kind") == kind and doc["metadata"]["name"] == name]


def _cronjob(docs: list[dict[str, Any]]) -> dict[str, Any]:
    found = _named(docs, "CronJob", BACKUP_NAME)
    assert len(found) == 1
    return found[0]


def _restore_job(docs: list[dict[str, Any]]) -> dict[str, Any]:
    found = _named(docs, "Job", RESTORE_NAME)
    assert len(found) == 1
    return found[0]


def _containers(pod_spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = pod_spec.get("initContainers", []) + pod_spec.get("containers", [])
    return {container["name"]: container for container in items}


def _env(container: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["name"]: item for item in container.get("env", [])}


def _script(container: dict[str, Any]) -> str:
    return "\n".join(container["command"])


def test_local_render_has_no_backup_or_restore_object() -> None:
    docs = render_chart()

    assert _named(docs, "CronJob", BACKUP_NAME) == []
    assert _named(docs, "Job", RESTORE_NAME) == []


def test_hosted_render_has_one_backup_cronjob_with_the_schedule_and_endpoint(
    tmp_path: Path,
) -> None:
    docs = render_chart("-f", str(hosted_values_file(tmp_path)))
    job = _cronjob(docs)

    assert job["spec"]["schedule"] == DEFAULT_SCHEDULE
    assert job["spec"]["concurrencyPolicy"] == "Forbid"
    assert job["spec"]["jobTemplate"]["spec"]["backoffLimit"] == 3
    upload = _containers(job["spec"]["jobTemplate"]["spec"]["template"]["spec"])["upload"]
    assert _env(upload)["MC_HOST_backup"]["value"] == (
        "https://$(BACKUP_ACCESS_KEY):$(BACKUP_SECRET_KEY)@hosted-test"
    )


def test_hosted_render_reads_the_schedule_from_values(tmp_path: Path) -> None:
    docs = render_chart(
        "-f",
        str(hosted_values_file(tmp_path, **{"backup.schedule": "5 4 * * 1"})),
    )

    assert _cronjob(docs)["spec"]["schedule"] == "5 4 * * 1"


def test_backup_credentials_come_only_from_the_named_secret(tmp_path: Path) -> None:
    docs = render_chart("-f", str(hosted_values_file(tmp_path)))
    pod_spec = _cronjob(docs)["spec"]["jobTemplate"]["spec"]["template"]["spec"]
    containers = _containers(pod_spec)

    upload_env = _env(containers["upload"])
    assert upload_env["BACKUP_ACCESS_KEY"]["valueFrom"]["secretKeyRef"] == {
        "name": SECRET_NAME,
        "key": "access-key",
    }
    assert upload_env["BACKUP_SECRET_KEY"]["valueFrom"]["secretKeyRef"] == {
        "name": SECRET_NAME,
        "key": "secret-key",
    }
    for name in ("BACKUP_ACCESS_KEY", "BACKUP_SECRET_KEY"):
        assert "value" not in upload_env[name]


def test_backup_job_never_echoes_a_credential(tmp_path: Path) -> None:
    docs = render_chart("-f", str(hosted_values_file(tmp_path)))
    pod_spec = _cronjob(docs)["spec"]["jobTemplate"]["spec"]["template"]["spec"]

    dump_script = _script(_containers(pod_spec)["dump"])
    assert "BACKUP_" not in dump_script
    assert "PGPASSWORD" not in dump_script


def test_backup_dumps_every_database_in_custom_format(tmp_path: Path) -> None:
    docs = render_chart("-f", str(hosted_values_file(tmp_path)))
    pod_spec = _cronjob(docs)["spec"]["jobTemplate"]["spec"]["template"]["spec"]

    dump_script = _script(_containers(pod_spec)["dump"])
    assert "pg_dump --format=custom" in dump_script
    assert "datallowconn AND NOT datistemplate" in dump_script
    assert "backup-object postgres/" in dump_script


def test_backup_uploads_to_the_bucket_prefix(tmp_path: Path) -> None:
    docs = render_chart("-f", str(hosted_values_file(tmp_path)))
    pod_spec = _cronjob(docs)["spec"]["jobTemplate"]["spec"]["template"]["spec"]

    args = _containers(pod_spec)["upload"]["args"]
    assert args[-2:] == ["/backup/", "backup/hosted-test/postgres/"]


def test_backup_is_unencrypted_by_default(tmp_path: Path) -> None:
    docs = render_chart("-f", str(hosted_values_file(tmp_path)))
    pod_spec = _cronjob(docs)["spec"]["jobTemplate"]["spec"]["template"]["spec"]

    dump = _containers(pod_spec)["dump"]
    assert "openssl" not in _script(dump)
    assert "BACKUP_ENCRYPTION_PASSPHRASE" not in _env(dump)


def test_backup_encrypts_each_dump_when_encryption_is_enabled(tmp_path: Path) -> None:
    docs = render_chart(
        "-f",
        str(hosted_values_file(tmp_path, **{"backup.encryption.enabled": True})),
    )
    pod_spec = _cronjob(docs)["spec"]["jobTemplate"]["spec"]["template"]["spec"]

    dump = _containers(pod_spec)["dump"]
    assert "openssl enc -aes-256-cbc -pbkdf2 -salt" in _script(dump)
    assert _env(dump)["BACKUP_ENCRYPTION_PASSPHRASE"]["valueFrom"]["secretKeyRef"] == {
        "name": SECRET_NAME,
        "key": "encryption-passphrase",
    }


def test_restore_job_is_absent_by_default(tmp_path: Path) -> None:
    docs = render_chart("-f", str(hosted_values_file(tmp_path)))

    assert _named(docs, "Job", RESTORE_NAME) == []


def test_restore_job_renders_only_when_enabled_and_names_the_object(tmp_path: Path) -> None:
    docs = render_chart("-f", str(hosted_values_file(tmp_path)), *RESTORE_ARGS)
    job = _restore_job(docs)

    annotations = job["metadata"]["annotations"]
    assert annotations["helm.sh/hook"] == "post-install"
    assert job["spec"]["backoffLimit"] == 0
    download = _containers(job["spec"]["template"]["spec"])["download"]
    assert download["args"][-2] == "backup/hosted-test/postgres/2026-11-18/"


def test_restore_job_runs_pg_restore_into_each_named_database(tmp_path: Path) -> None:
    docs = render_chart("-f", str(hosted_values_file(tmp_path)), *RESTORE_ARGS)
    restore = _containers(_restore_job(docs)["spec"]["template"]["spec"])["restore"]

    script = _script(restore)
    assert "pg_restore --clean --if-exists --no-owner --exit-on-error" in script
    assert 'basename "$dump" .dump' in script


def test_restore_job_reads_the_passphrase_only_when_encryption_is_enabled() -> None:
    """The script decrypts any .enc object it finds. The passphrase comes from the Secret only then."""
    plain = _containers(
        _restore_job(render_chart(*LOCAL_BACKUP_ARGS, *RESTORE_ARGS))["spec"]["template"]["spec"]
    )["restore"]
    encrypted = _containers(
        _restore_job(
            render_chart(
                *LOCAL_BACKUP_ARGS, *RESTORE_ARGS, "--set", "backup.encryption.enabled=true"
            )
        )["spec"]["template"]["spec"]
    )["restore"]

    assert "BACKUP_ENCRYPTION_PASSPHRASE" not in _env(plain)
    assert _env(encrypted)["BACKUP_ENCRYPTION_PASSPHRASE"]["valueFrom"]["secretKeyRef"] == {
        "name": SECRET_NAME,
        "key": "encryption-passphrase",
    }


def test_restore_job_fails_the_render_without_a_backup_object_name() -> None:
    proc = helm_template_result(*LOCAL_BACKUP_ARGS, "--set", "restore.enabled=true")

    assert proc.returncode != 0
    assert "restore.objectPrefix" in proc.stderr


def test_hosted_guard_rejects_a_disabled_backup(tmp_path: Path) -> None:
    proc = helm_template_result(
        "-f",
        str(hosted_values_file(tmp_path, **{"backup.enabled": False})),
    )

    assert proc.returncode != 0
    assert "backup.enabled" in proc.stderr


def test_hosted_guard_rejects_an_http_endpoint(tmp_path: Path) -> None:
    proc = helm_template_result(
        "-f",
        str(hosted_values_file(tmp_path, **{"backup.endpoint": "http://hosted-test"})),
    )

    assert proc.returncode != 0
    assert "backup.endpoint" in proc.stderr


def test_hosted_guard_rejects_a_cluster_internal_endpoint(tmp_path: Path) -> None:
    proc = helm_template_result(
        "-f",
        str(
            hosted_values_file(
                tmp_path,
                **{"backup.endpoint": "https://silo.runefoble.svc.cluster.local:9000"},
            )
        ),
    )

    assert proc.returncode != 0
    assert "backup.endpoint" in proc.stderr


def test_hosted_guard_rejects_a_placeholder_bucket(tmp_path: Path) -> None:
    proc = helm_template_result(
        "-f",
        str(hosted_values_file(tmp_path, **{"backup.bucket": "REPLACE-ME"})),
    )

    assert proc.returncode != 0
    assert "backup.bucket" in proc.stderr


def test_hosted_guard_rejects_a_placeholder_restore_prefix(tmp_path: Path) -> None:
    proc = helm_template_result(
        "-f",
        str(
            hosted_values_file(
                tmp_path,
                **{"restore.enabled": True, "restore.objectPrefix": "REPLACE-ME"},
            )
        ),
    )

    assert proc.returncode != 0
    assert "restore.objectPrefix" in proc.stderr


def test_hosted_render_with_restore_enabled_renders_the_restore_job(tmp_path: Path) -> None:
    docs = render_chart(
        "-f",
        str(
            hosted_values_file(
                tmp_path,
                **{"restore.enabled": True, "restore.objectPrefix": "postgres/2026-11-18"},
            )
        ),
    )

    assert _restore_job(docs)["metadata"]["name"] == RESTORE_NAME
