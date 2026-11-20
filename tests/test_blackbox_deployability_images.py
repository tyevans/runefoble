"""Blackbox deployability tests for the shared Python service image (TASK-0620).

Governed by ADR-0003 (uv workspace) and ADR-0005 (Kind and Helm).
The Docker-marked tests build an image, run it, and call `/openapi.json` over HTTP.
They use no private state and no backdoors.
"""

from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from tests.helpers.helm import helm_template_result, render_chart
from tests.helpers.ports import free_port
from tests.helpers.process import run_command

REPO_ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = REPO_ROOT / "Makefile"
DOCKERFILE = REPO_ROOT / "deployments" / "docker" / "python-service.Dockerfile"
VALUES = REPO_ROOT / "deployments" / "helm" / "runefoble" / "values.yaml"
IMAGE_TAG = "0.1.0"
# Helm images that are not built by `make images`.
NON_PYTHON_OR_OUT_OF_SCOPE = {"frontend", "audience-studio"}
ROW_RE = re.compile(
    r"'(?P<name>[a-z-]+)\|(?P<service>[a-z-]+)\|(?P<app>[a-z_.]+:\w+)\|(?P<port>\d+)"
    r"\|(?P<packages>[a-z0-9 -]*)'",
)


@dataclass(frozen=True)
class ImageRow:
    name: str
    service: str
    app: str
    port: int
    system_packages: str = ""

    @property
    def tag(self) -> str:
        return f"runefoble/{self.name}:{IMAGE_TAG}"


def read_image_table() -> list[ImageRow]:
    """Read the IMAGE_TABLE rows that `make images` builds."""
    rows = [
        ImageRow(m["name"], m["service"], m["app"], int(m["port"]), m["packages"].strip())
        for m in ROW_RE.finditer(MAKEFILE.read_text(encoding="utf-8"))
    ]
    assert rows, "Makefile declares no IMAGE_TABLE rows"
    return rows


def helm_service_ports() -> dict[str, int]:
    """Return image name -> container port from values.yaml `services`."""
    values = yaml.safe_load(VALUES.read_text(encoding="utf-8"))
    ports: dict[str, int] = {}
    for config in values["services"].values():
        if "image" not in config:  # entries without an image are not deployed
            continue
        image = config["image"]
        name = image.removeprefix("runefoble/").removesuffix(f":{IMAGE_TAG}")
        ports[name] = int(config["port"])
    return ports


def docker_daemon_available() -> bool:
    if shutil.which("docker") is None:
        return False
    result = run_command(["docker", "info"], timeout=60)
    return result.returncode == 0


def test_image_table_matches_helm_services():
    """Every Python Helm image has one table row, and the ports match values.yaml."""
    rows = {row.name: row for row in read_image_table()}
    helm_ports = helm_service_ports()

    python_helm = set(helm_ports) - NON_PYTHON_OR_OUT_OF_SCOPE
    assert set(rows) == python_helm, "IMAGE_TABLE names differ from Helm service images"
    for name, row in rows.items():
        assert row.port == helm_ports[name], f"{name}: table port {row.port} != Helm port"


def test_make_images_dry_run_lists_every_row_and_kind_load():
    """`make -n images` prints each table row, a docker build and a kind load."""
    result = run_command(["make", "-n", "images"], cwd=REPO_ROOT, timeout=60)
    assert result.returncode == 0, f"`make -n images` failed: {result.stderr}"
    output = result.stdout
    assert "docker build" in output
    assert str(DOCKERFILE.relative_to(REPO_ROOT)) in output
    assert "kind load docker-image" in output
    assert "--name runefoble-local" in output
    for row in read_image_table():
        assert f"{row.name}|{row.service}|{row.app}|{row.port}" in output


def test_make_help_documents_images_target():
    """`make help` lists the images target."""
    result = run_command(["make", "help"], cwd=REPO_ROOT, timeout=60)
    assert result.returncode == 0
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    assert re.search(r"^\s*images\s+Build .*Kind", plain, re.MULTILINE), (
        "`make help` does not document the images target"
    )


def test_helm_template_image_tags_match_built_tags():
    """Image tags in `helm template` equal the tags that `make images` builds."""
    result = helm_template_result()
    assert result.returncode == 0, f"helm template failed: {result.stderr}"
    rendered = set(re.findall(r"image: (runefoble/[\w-]+:[\w.]+)", result.stdout))
    built = {row.tag for row in read_image_table()}
    assert built <= rendered, f"built tags not used by Helm: {built - rendered}"


def build_image(row: ImageRow) -> None:
    """Build one service image through the shared Dockerfile, as `make images` does."""
    build = run_command(
        [
            "docker",
            "build",
            "-f",
            str(DOCKERFILE),
            "--build-arg",
            f"SERVICE={row.service}",
            "--build-arg",
            f"APP={row.app}",
            "--build-arg",
            f"PORT={row.port}",
            "--build-arg",
            f"SYSTEM_PACKAGES={row.system_packages}",
            "-t",
            row.tag,
            str(REPO_ROOT),
        ],
        timeout=1800,
    )
    assert build.returncode == 0, f"docker build failed:\n{build.stderr[-4000:]}"


# MCP over streamable HTTP has no OpenAPI document (Hard Invariant 5 exemption, TASK-0623).
# Its own blackbox suite checks the MCP handshake instead.
NO_OPENAPI = {"gateway-mcp"}


@pytest.mark.docker
@pytest.mark.skipif(not docker_daemon_available(), reason="Docker daemon is not reachable")
@pytest.mark.parametrize(
    "row", [r for r in read_image_table() if r.name not in NO_OPENAPI], ids=lambda row: row.name
)
def test_built_image_serves_openapi_on_helm_port(row: ImageRow):
    """A built image starts and serves `/openapi.json` on its Helm port."""
    build_image(row)

    host_port = free_port()
    container = run_command(
        ["docker", "run", "-d", "-p", f"127.0.0.1:{host_port}:{row.port}", row.tag], timeout=120
    )
    assert container.returncode == 0, f"docker run failed: {container.stderr}"
    container_id = container.stdout.strip()
    try:
        document = _wait_for_openapi(f"http://127.0.0.1:{host_port}/openapi.json", container_id)
        assert "paths" in document
    finally:
        subprocess.run(["docker", "rm", "-f", container_id], capture_output=True, timeout=120)


def _voice_agent_row() -> ImageRow:
    (row,) = [r for r in read_image_table() if r.name == "voice-agent"]
    return row


@pytest.mark.docker
@pytest.mark.skipif(not docker_daemon_available(), reason="Docker daemon is not reachable")
def test_voice_agent_image_synthesizes_speech_with_espeak():
    """The voice-agent image ships espeak-ng. `POST /api/v1/voice/synthesize` returns a WAV payload."""
    row = _voice_agent_row()
    assert "espeak-ng" in row.system_packages.split()
    build_image(row)

    host_port = free_port()
    container = run_command(
        ["docker", "run", "-d", "-p", f"127.0.0.1:{host_port}:{row.port}", row.tag], timeout=120
    )
    assert container.returncode == 0, f"docker run failed: {container.stderr}"
    container_id = container.stdout.strip()
    try:
        _wait_for_openapi(f"http://127.0.0.1:{host_port}/openapi.json", container_id)
        request = urllib.request.Request(
            f"http://127.0.0.1:{host_port}/api/v1/voice/synthesize",
            data=json.dumps({"text": "The gate creaks open.", "persona_id": "watcher_dm"}).encode(
                "utf-8"
            ),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            assert response.status == 200
            body = json.loads(response.read().decode("utf-8"))
        wav = base64.b64decode(body["audio_base64"])
        assert wav[:4] == b"RIFF" and wav[8:12] == b"WAVE"
        assert body["engine"] == "espeak-ng"
        assert body["duration_ms"] > 0
    finally:
        subprocess.run(["docker", "rm", "-f", container_id], capture_output=True, timeout=120)


def _rendered_helm_documents() -> list[dict]:
    return render_chart()


def test_voice_agent_chart_mounts_model_cache_and_probes_readiness():
    """The voice agent Deployment mounts a model cache PVC, disables download, and probes /readyz."""
    documents = _rendered_helm_documents()
    pvcs = [d for d in documents if d.get("kind") == "PersistentVolumeClaim"]
    deployments = {d["metadata"]["name"]: d for d in documents if d.get("kind") == "Deployment"}
    voice = deployments["voice-agent"]["spec"]["template"]["spec"]
    container = voice["containers"][0]

    claim_names = {pvc["metadata"]["name"] for pvc in pvcs}
    volume = next(v for v in voice["volumes"] if "persistentVolumeClaim" in v)
    assert volume["persistentVolumeClaim"]["claimName"] in claim_names

    mount = next(m for m in container["volumeMounts"] if m["name"] == volume["name"])
    env = {item["name"]: item.get("value") for item in container["env"]}
    assert env["RUNEFOBLE_VOICE_STT_MODEL_DIR"] == mount["mountPath"]
    assert env["RUNEFOBLE_VOICE_STT_DOWNLOAD_ENABLED"] == "false"
    assert env["RUNEFOBLE_VOICE_STT_MODEL_SIZE"]

    probe = container["readinessProbe"]["httpGet"]
    assert probe["path"] == "/readyz"
    assert probe["port"] == 8005
    assert voice["securityContext"]["fsGroup"] == 10001


def _wait_for_openapi(url: str, container_id: str) -> dict:
    return json.loads(_wait_for_http(url, container_id))


def _wait_for_http(url: str, container_id: str, timeout_s: float = 90.0) -> str:
    """Poll `url` until it returns HTTP 200 and return the body as text."""
    deadline = time.monotonic() + timeout_s
    last_error = "no response"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                assert response.status == 200
                return response.read().decode("utf-8")
        except (urllib.error.URLError, ConnectionError, OSError) as exc:
            last_error = str(exc)
        state = run_command(
            ["docker", "inspect", "-f", "{{.State.Running}}", container_id], timeout=30
        ).stdout.strip()
        if state != "true":
            logs = run_command(["docker", "logs", container_id], timeout=30)
            raise AssertionError(f"container exited early:\n{(logs.stdout + logs.stderr)[-4000:]}")
        time.sleep(1.0)
    raise AssertionError(f"{url} not served within {timeout_s}s: {last_error}")


AUDIENCE_DOCKERFILE = REPO_ROOT / "services" / "audience_studio" / "Dockerfile"
AUDIENCE_PORT = 8010
AUDIENCE_TAG = f"runefoble/audience-studio:{IMAGE_TAG}"


def test_make_images_builds_audience_studio_from_node_dockerfile():
    """`make -n images` builds the Node audience-studio image and loads it into Kind."""
    result = run_command(["make", "-n", "images"], cwd=REPO_ROOT, timeout=60)
    assert result.returncode == 0, f"`make -n images` failed: {result.stderr}"
    output = result.stdout
    assert f"-f {AUDIENCE_DOCKERFILE.relative_to(REPO_ROOT)}" in output
    assert f"-t {AUDIENCE_TAG}" in output
    assert f"kind load docker-image {AUDIENCE_TAG} --name runefoble-local" in output


def test_audience_studio_dockerfile_runs_non_root_on_helm_port():
    """The Node image runs `dist/index.js` as a non-root user on the Helm port."""
    text = AUDIENCE_DOCKERFILE.read_text(encoding="utf-8")
    assert "FROM node:22-alpine" in text
    assert f"PORT={AUDIENCE_PORT}" in text
    assert re.search(r"^USER\s+(?!root\b)\S+", text, re.MULTILINE), "no non-root USER"
    assert 'CMD ["node", "dist/index.js"]' in text


@pytest.mark.docker
@pytest.mark.skipif(not docker_daemon_available(), reason="Docker daemon is not reachable")
def test_built_audience_studio_image_serves_health_and_openapi():
    """The audience-studio image starts, reports healthy and serves `/openapi.json`."""
    build = run_command(
        ["docker", "build", "-f", str(AUDIENCE_DOCKERFILE), "-t", AUDIENCE_TAG, str(REPO_ROOT)],
        timeout=1800,
    )
    assert build.returncode == 0, f"docker build failed:\n{build.stderr[-4000:]}"

    host_port = free_port()
    container = run_command(
        [
            "docker",
            "run",
            "-d",
            "-e",
            "RUNEFOBLE_SPICEDB_PRESHARED_KEY=blackbox-test-key",
            "-p",
            f"127.0.0.1:{host_port}:{AUDIENCE_PORT}",
            AUDIENCE_TAG,
        ],
        timeout=120,
    )
    assert container.returncode == 0, f"docker run failed: {container.stderr}"
    container_id = container.stdout.strip()
    try:
        document = _wait_for_openapi(f"http://127.0.0.1:{host_port}/openapi.json", container_id)
        assert "paths" in document
        for path in ("/healthz", "/readyz"):
            with urllib.request.urlopen(f"http://127.0.0.1:{host_port}{path}", timeout=10) as r:
                assert r.status == 200, path
    finally:
        subprocess.run(["docker", "rm", "-f", container_id], capture_output=True, timeout=120)


FRONTEND_DOCKERFILE = REPO_ROOT / "frontend" / "Dockerfile"
FRONTEND_TAG = f"runefoble/frontend:{IMAGE_TAG}"


def test_make_images_builds_frontend_from_app_shell_dockerfile():
    """`make -n images` builds the App Shell image and loads it into Kind."""
    result = run_command(["make", "-n", "images"], cwd=REPO_ROOT, timeout=60)
    assert result.returncode == 0, f"`make -n images` failed: {result.stderr}"
    output = result.stdout
    assert f"-f {FRONTEND_DOCKERFILE.relative_to(REPO_ROOT)}" in output
    assert f"-t {FRONTEND_TAG}" in output
    assert f"kind load docker-image {FRONTEND_TAG} --name runefoble-local" in output


@pytest.mark.docker
@pytest.mark.skipif(not docker_daemon_available(), reason="Docker daemon is not reachable")
def test_built_frontend_image_serves_app_shell_index_html():
    """The App Shell image serves index.html on port 80, including deep links."""
    build = run_command(
        ["docker", "build", "-f", str(FRONTEND_DOCKERFILE), "-t", FRONTEND_TAG, str(REPO_ROOT)],
        timeout=1800,
    )
    assert build.returncode == 0, f"docker build failed:\n{build.stderr[-4000:]}"

    host_port = free_port()
    container = run_command(
        ["docker", "run", "-d", "-p", f"127.0.0.1:{host_port}:80", FRONTEND_TAG], timeout=120
    )
    assert container.returncode == 0, f"docker run failed: {container.stderr}"
    container_id = container.stdout.strip()
    try:
        root = _wait_for_http(f"http://127.0.0.1:{host_port}/", container_id)
        assert "<runefoble-app>" in root
        assert "<title>Runefoble" in root
        deep_link = _wait_for_http(f"http://127.0.0.1:{host_port}/campaigns/1", container_id)
        assert "<runefoble-app>" in deep_link
    finally:
        subprocess.run(["docker", "rm", "-f", container_id], capture_output=True, timeout=120)


def test_images_push_dry_run_lists_every_row_a_push_and_the_digest_step():
    """`make -n images-push` prints each image row, a docker push and the digest recorder. It runs nothing."""
    result = run_command(
        ["make", "-n", "images-push", "IMAGE_REGISTRY=registry.example.com/team"],
        cwd=REPO_ROOT,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    output = result.stdout
    assert "docker push" in output
    assert "docker build" in output
    assert "scripts/record_image_digests.py" in output
    assert "registry.example.com/team/runefoble" in output
    assert "services/audience_studio/Dockerfile" in output
    assert "frontend/Dockerfile" in output
    assert "kind load" not in output
    for row in read_image_table():
        assert f"{row.name}|{row.service}|{row.app}|{row.port}" in output


def test_images_push_refuses_to_run_without_a_registry():
    """`make images-push` stops before any build when IMAGE_REGISTRY is empty."""
    result = run_command(["make", "images-push"], cwd=REPO_ROOT, timeout=60)

    assert result.returncode != 0
    assert "IMAGE_REGISTRY" in (result.stdout + result.stderr)
