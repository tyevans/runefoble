"""Blackbox checks for the voice agent speech-to-text engine in the rendered Helm chart (TASK-0833).

The tests render the umbrella chart with `helm template` and read only the public manifest
output. The engine choice decides the environment variables and whether the pod mounts the
faster-whisper model cache.
"""

import shutil
from pathlib import Path

import pytest
import yaml

from tests.helpers.process import run_command

HELM_CHART = Path("deployments/helm/runefoble")
WHISPER_BASE_URL = "http://whisper.test:8080"


def _render(*set_args: str) -> list[dict]:
    if not shutil.which("helm"):
        pytest.skip("helm CLI not available")
    args = ["helm", "template", "runefoble", str(HELM_CHART)]
    for value in set_args:
        args += ["--set-string", value]
    proc = run_command(args, check=True, timeout=240.0)
    return [doc for doc in yaml.safe_load_all(proc.stdout) if doc]


def _voice_deployment(docs: list[dict]) -> dict:
    (deployment,) = [
        d for d in docs if d.get("kind") == "Deployment" and d["metadata"]["name"] == "voice-agent"
    ]
    return deployment


def _voice_env(docs: list[dict]) -> dict[str, str]:
    container = _voice_deployment(docs)["spec"]["template"]["spec"]["containers"][0]
    return {item["name"]: item.get("value") for item in container["env"]}


def _model_cache_volume_names(docs: list[dict]) -> set[str]:
    pod = _voice_deployment(docs)["spec"]["template"]["spec"]
    mounts = {m["name"] for m in pod["containers"][0].get("volumeMounts", [])}
    volumes = {v["name"] for v in pod.get("volumes", [])}
    return {"model-cache"} & (mounts | volumes)


def _model_cache_claims(docs: list[dict]) -> list[str]:
    return [
        d["metadata"]["name"]
        for d in docs
        if d.get("kind") == "PersistentVolumeClaim"
        and d["metadata"]["name"] == "voice-agent-model-cache"
    ]


def test_default_render_uses_faster_whisper_with_the_model_cache():
    docs = _render()

    env = _voice_env(docs)
    assert env["RUNEFOBLE_VOICE_STT_ENGINE"] == "faster-whisper"
    assert "RUNEFOBLE_VOICE_STT_BASE_URL" not in env
    assert _model_cache_volume_names(docs) == {"model-cache"}
    assert _model_cache_claims(docs) == ["voice-agent-model-cache"]


def test_whisper_cpp_render_passes_base_url_and_drops_the_model_cache():
    docs = _render(
        "services.voiceAgent.sttEngine=whisper-cpp",
        f"services.voiceAgent.sttBaseUrl={WHISPER_BASE_URL}",
    )

    env = _voice_env(docs)
    assert env["RUNEFOBLE_VOICE_STT_ENGINE"] == "whisper-cpp"
    assert env["RUNEFOBLE_VOICE_STT_BASE_URL"] == WHISPER_BASE_URL
    assert _model_cache_volume_names(docs) == set()
    assert _model_cache_claims(docs) == []
