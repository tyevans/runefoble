"""Blackbox checks for hosted image references and pull Secrets (TASK-0960).

The tests render the umbrella chart with `helm template`, run the image recorder script on a
copy of the image values file, and read `make -n images-push`. The chart and the script are
the public interfaces. No test reaches a registry or pushes an image.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.helpers.helm import (
    CHART_DIR,
    HOSTED_IMAGES,
    HOSTED_TEST_REGISTRY,
    helm_template_result,
    hosted_values_file,
    render_chart,
)

REPO_ROOT = CHART_DIR.parents[2]
RECORDER = REPO_ROOT / "scripts" / "record_image_digests.py"
WORKLOAD_KINDS = {"Deployment", "StatefulSet", "Job"}
DIGEST = "sha256:" + "a" * 64
PULL_SECRET = {"name": "runefoble-registry"}


def _pod_specs(documents: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return a pod spec for each Deployment, StatefulSet and Job, keyed by kind and name."""
    specs: dict[str, dict[str, Any]] = {}
    for doc in documents:
        if doc.get("kind") in WORKLOAD_KINDS:
            specs[f"{doc['kind']}/{doc['metadata']['name']}"] = doc["spec"]["template"]["spec"]
    return specs


def _images(pod_spec: dict[str, Any]) -> list[str]:
    containers = pod_spec.get("initContainers", []) + pod_spec["containers"]
    return [container["image"] for container in containers]


def _hosted_render(tmp_path: Path, **overrides: object) -> list[dict[str, Any]]:
    return render_chart("-f", str(hosted_values_file(tmp_path, **overrides)))


def test_hosted_render_names_registry_and_digest_for_every_image(tmp_path: Path):
    """Every image in a hosted render has a registry host and a digest."""
    images = [
        image for spec in _pod_specs(_hosted_render(tmp_path)).values() for image in _images(spec)
    ]

    assert images
    for image in images:
        host = image.split("/")[0]
        assert "." in host or ":" in host, f"no registry host: {image}"
        assert "@sha256:" in image, f"no digest: {image}"
    runefoble = [image for image in images if "/runefoble/" in image]
    assert runefoble
    assert all(image.startswith(f"{HOSTED_TEST_REGISTRY}/runefoble/") for image in runefoble)


def test_committed_images_file_pins_every_third_party_image_by_digest():
    """Each third-party image in values.images.yaml carries a digest. Only Runefoble lines wait."""
    text = HOSTED_IMAGES.read_text(encoding="utf-8")
    values = yaml.safe_load(text)

    third_party = {
        "postgres": values["postgres"]["image"],
        "redis": values["redis"]["image"],
        "zitadel": values["zitadel"]["image"],
        "spicedb": values["spicedb"]["image"],
        "spicedb.schemaJob": values["spicedb"]["schemaJob"]["image"],
        "openpanel": values["openpanel"]["image"],
        "mailpit": values["mailpit"]["image"],
        "observability.otelCollector": values["observability"]["otelCollector"]["image"],
        "observability.loki": values["observability"]["loki"]["image"],
        "observability.grafana": values["observability"]["grafana"]["image"],
        "swaggerUI": values["swaggerUI"]["image"],
    }
    for key, image in third_party.items():
        assert "@sha256:" in image, f"{key} has no digest: {image}"
        assert "REPLACE-ME" not in image, f"{key} still holds a placeholder"


@pytest.mark.parametrize(
    ("dotted", "value", "key"),
    [
        ("postgres.image", "docker.io/pgvector/pgvector:pg16", "postgres.image"),
        ("swaggerUI.image", "docker.io/swaggerapi/swagger-ui:v5.17.14", "swaggerUI.image"),
        (
            "services.gatewayApi.image",
            f"runefoble/gateway-api:0.1.0@{DIGEST}",
            "services.gatewayApi.image",
        ),
        (
            "frontend.image",
            f"localhost:5000/runefoble/frontend:0.1.0@{DIGEST}",
            "frontend.image",
        ),
    ],
)
def test_hosted_guard_rejects_an_image_without_registry_or_digest(
    tmp_path: Path, dotted: str, value: str, key: str
):
    """A hosted render fails on the first image that has no digest, no registry or a dev host."""
    proc = helm_template_result("-f", str(hosted_values_file(tmp_path, **{dotted: value})))

    assert proc.returncode != 0
    assert key in proc.stderr


def test_local_render_needs_no_image_references():
    """The local render keeps the local names and renders without a hosted file."""
    documents = render_chart()
    images = [image for spec in _pod_specs(documents).values() for image in _images(spec)]

    assert "runefoble/gateway-api:0.1.0" in images
    assert not any("@sha256:" in image for image in images if "/runefoble/" in image)


def test_pull_secrets_render_on_every_pod_spec(tmp_path: Path):
    """With global.imagePullSecrets set, every Deployment, StatefulSet and Job pod spec carries it."""
    specs = _pod_specs(_hosted_render(tmp_path, **{"global.imagePullSecrets": [PULL_SECRET]}))

    kinds = {key.split("/")[0] for key in specs}
    assert kinds == WORKLOAD_KINDS
    for key, spec in specs.items():
        assert spec.get("imagePullSecrets") == [PULL_SECRET], key


def test_pull_secrets_absent_when_unset(tmp_path: Path):
    """Without global.imagePullSecrets, no pod spec renders the key, in hosted and local renders."""
    hosted = _pod_specs(_hosted_render(tmp_path))
    local = _pod_specs(render_chart())

    for specs in (hosted, local):
        assert specs
        assert all("imagePullSecrets" not in spec for spec in specs.values())


def test_record_image_digests_replaces_the_runefoble_line(tmp_path: Path):
    """The recorder writes the full reference for the image, and keeps every other line."""
    values_file = tmp_path / "values.images.yaml"
    shutil.copy(HOSTED_IMAGES, values_file)

    proc = subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(RECORDER),
            str(values_file),
            "gateway-api",
            "registry.example.com/team",
            "0.1.0",
            DIGEST,
        ],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=REPO_ROOT,
    )

    assert proc.returncode == 0, proc.stderr
    values = yaml.safe_load(values_file.read_text(encoding="utf-8"))
    assert values["services"]["gatewayApi"]["image"] == (
        f"registry.example.com/team/runefoble/gateway-api:0.1.0@{DIGEST}"
    )
    assert values["services"]["theWatcher"]["image"].startswith("REPLACE-ME/runefoble/the-watcher")
    assert values["postgres"]["image"].startswith("docker.io/pgvector/pgvector:pg16@sha256:")


def test_record_image_digests_rejects_a_value_that_is_not_a_digest(tmp_path: Path):
    """The recorder refuses a digest that is not sha256 hex."""
    values_file = tmp_path / "values.images.yaml"
    shutil.copy(HOSTED_IMAGES, values_file)

    proc = subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(RECORDER),
            str(values_file),
            "gateway-api",
            "registry.example.com/team",
            "0.1.0",
            "latest",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=REPO_ROOT,
    )

    assert proc.returncode != 0
    assert "not a sha256 digest" in proc.stderr
