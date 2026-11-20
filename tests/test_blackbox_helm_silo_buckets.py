"""The Helm chart creates the Silo buckets with a plain Job (TASK-0924, TASK-0933, ADR-0005).

Without the buckets, every Silo write fails and every forge request answers 503. The Job
creates each bucket in `silo.buckets` and skips a bucket that exists. It reads the Silo keys
from the credentials Secret. It is not a Helm hook: asset-forge waits for the bucket, so a
post-install hook would wait for asset-forge and `helm install --wait` would never finish.
"""

from __future__ import annotations

from tests.helpers.helm import render_chart

EXPECTED_BUCKETS = ["runefoble-assets", "runefoble-recordings"]


def _bucket_jobs(*extra_args: str) -> list[dict]:
    return [
        doc
        for doc in render_chart(*extra_args)
        if doc.get("kind") == "Job" and doc["metadata"]["name"].startswith("silo-buckets-")
    ]


def _container(job: dict) -> dict:
    containers = job["spec"]["template"]["spec"]["containers"]
    assert len(containers) == 1
    return containers[0]


def test_bucket_job_is_a_plain_job_and_not_a_helm_hook() -> None:
    jobs = _bucket_jobs()
    assert len(jobs) == 1
    assert "helm.sh/hook" not in jobs[0]["metadata"].get("annotations", {})
    assert jobs[0]["spec"]["template"]["spec"]["restartPolicy"] == "OnFailure"


def test_bucket_job_name_changes_when_the_bucket_list_changes() -> None:
    """A Job spec is immutable, so a new bucket list gets a new Job name."""
    base = _bucket_jobs()[0]["metadata"]["name"]
    changed = _bucket_jobs("--set", "silo.buckets={only-one}")[0]["metadata"]["name"]
    assert base != changed
    assert base == _bucket_jobs()[0]["metadata"]["name"]


def test_bucket_job_creates_every_bucket_and_skips_existing_ones() -> None:
    args = _container(_bucket_jobs()[0])["args"]
    assert "mb" in args
    assert "--ignore-existing" in args
    assert [a for a in args if a.startswith("silo/")] == [f"silo/{b}" for b in EXPECTED_BUCKETS]


def test_bucket_job_follows_the_bucket_list_in_values() -> None:
    args = _container(_bucket_jobs("--set", "silo.buckets={only-one}")[0])["args"]
    assert [a for a in args if a.startswith("silo/")] == ["silo/only-one"]


def test_bucket_job_uses_a_digest_pinned_client_image() -> None:
    image = _container(_bucket_jobs()[0])["image"]
    assert image.startswith("cgr.dev/chainguard/minio-client@sha256:")


def test_bucket_job_reads_the_silo_keys_from_the_credentials_secret() -> None:
    env = {e["name"]: e for e in _container(_bucket_jobs()[0])["env"]}
    for name, key in (
        ("SILO_ACCESS_KEY", "silo-access-key"),
        ("SILO_SECRET_KEY", "silo-secret-key"),
    ):
        ref = env[name]["valueFrom"]["secretKeyRef"]
        assert ref["name"] == "runefoble-credentials"
        assert ref["key"] == key
    assert env["MC_HOST_silo"]["value"] == "http://$(SILO_ACCESS_KEY):$(SILO_SECRET_KEY)@silo:9000"
    assert "silo_secret_pass" not in str(env)


def test_bucket_job_is_absent_when_silo_is_disabled() -> None:
    assert _bucket_jobs("--set", "silo.enabled=false") == []
