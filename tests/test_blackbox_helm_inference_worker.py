"""Blackbox checks for the inference worker and Watcher settings in the Helm render (TASK-0948).

The tests read the rendered manifests of `helm template` only. A value that the operator sets
reaches the pod as an env entry. A value that is unset adds no entry, so the worker default applies.
A hosted render fails when the worker API key Secret is not named.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.helpers.helm import helm_template_result, hosted_values_file, render_chart

WORKER_SECRET = "inference-worker-openai"
API_KEY_ENV = "RUNEFOBLE_WORKER_OPENAI_API_KEY"


def _worker_env(docs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return the env entries of the inference-worker container, keyed by name."""
    deployment = next(
        doc
        for doc in docs
        if doc.get("kind") == "Deployment" and doc["metadata"]["name"] == "inference-worker"
    )
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    return {item["name"]: item for item in container["env"]}


def _watcher_env(docs: list[dict[str, Any]]) -> dict[str, str]:
    deployment = next(
        doc
        for doc in docs
        if doc.get("kind") == "Deployment" and doc["metadata"]["name"] == "the-watcher"
    )
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    return {item["name"]: item.get("value") for item in container["env"]}


def test_local_render_sets_no_worker_api_key(tmp_path: Path) -> None:
    """With no Secret named, the worker gets no API key from the chart. The worker default applies."""
    env = _worker_env(render_chart())

    assert API_KEY_ENV not in env


def test_hosted_render_reads_the_api_key_from_the_named_secret(tmp_path: Path) -> None:
    env = _worker_env(render_chart("-f", str(hosted_values_file(tmp_path))))

    assert env[API_KEY_ENV]["valueFrom"]["secretKeyRef"] == {
        "name": WORKER_SECRET,
        "key": "api-key",
    }


def test_hosted_render_sets_temperature_token_limit_and_timeout(tmp_path: Path) -> None:
    env = _worker_env(render_chart("-f", str(hosted_values_file(tmp_path))))

    assert env["RUNEFOBLE_WORKER_TEMPERATURE"]["value"] == "0.7"
    assert env["RUNEFOBLE_WORKER_MAX_TOKENS"]["value"] == "512"
    assert env["RUNEFOBLE_WORKER_TIMEOUT_SECONDS"]["value"] == "30"


def test_ollama_entries_appear_only_when_their_values_are_set(tmp_path: Path) -> None:
    unset = _worker_env(render_chart("-f", str(hosted_values_file(tmp_path))))
    assert "RUNEFOBLE_WORKER_OLLAMA_BASE_URL" not in unset
    assert "RUNEFOBLE_WORKER_OLLAMA_MODEL" not in unset

    set_dir = tmp_path / "set"
    set_dir.mkdir()
    env = _worker_env(
        render_chart(
            "-f",
            str(
                hosted_values_file(
                    set_dir,
                    **{
                        "services.inferenceWorker.ollamaBaseUrl": "http://ollama.example.org:11434",
                        "services.inferenceWorker.ollamaModel": "qwen-test",
                    },
                )
            ),
        )
    )
    assert env["RUNEFOBLE_WORKER_OLLAMA_BASE_URL"]["value"] == "http://ollama.example.org:11434"
    assert env["RUNEFOBLE_WORKER_OLLAMA_MODEL"]["value"] == "qwen-test"


def test_zero_temperature_is_passed_not_dropped(tmp_path: Path) -> None:
    """A temperature of 0 is a real setting. The chart must pass it, not drop it as empty."""
    env = _worker_env(
        render_chart(
            "-f",
            str(hosted_values_file(tmp_path, **{"services.inferenceWorker.temperature": 0})),
        )
    )

    assert env["RUNEFOBLE_WORKER_TEMPERATURE"]["value"] == "0"


def test_hosted_render_fails_without_a_worker_api_key_secret(tmp_path: Path) -> None:
    proc = helm_template_result(
        "-f",
        str(
            hosted_values_file(tmp_path, **{"services.inferenceWorker.openaiApiKeySecret.name": ""})
        ),
    )

    assert proc.returncode != 0
    assert "services.inferenceWorker.openaiApiKeySecret.name" in proc.stderr


def test_hosted_render_fails_with_a_placeholder_worker_api_key_secret(tmp_path: Path) -> None:
    proc = helm_template_result(
        "-f",
        str(
            hosted_values_file(
                tmp_path,
                **{"services.inferenceWorker.openaiApiKeySecret.name": "REPLACE-ME"},
            )
        ),
    )

    assert proc.returncode != 0
    assert "services.inferenceWorker.openaiApiKeySecret.name" in proc.stderr


def test_hosted_render_fails_without_the_worker_api_key_name(tmp_path: Path) -> None:
    proc = helm_template_result(
        "-f",
        str(
            hosted_values_file(tmp_path, **{"services.inferenceWorker.openaiApiKeySecret.key": ""})
        ),
    )

    assert proc.returncode != 0
    assert "services.inferenceWorker.openaiApiKeySecret.key" in proc.stderr


def test_watcher_budgets_are_set_in_the_hosted_render(tmp_path: Path) -> None:
    env = _watcher_env(render_chart("-f", str(hosted_values_file(tmp_path))))

    assert env["RUNEFOBLE_WATCHER_INTENT_TIMEOUT_S"] == "2.0"
    assert env["RUNEFOBLE_WATCHER_STAND_IN_TIMEOUT_S"] == "10.0"
    assert env["RUNEFOBLE_WATCHER_NARRATION_TIMEOUT_S"] == "10.0"
    assert env["RUNEFOBLE_WATCHER_BOARD_TIMEOUT_S"] == "2.0"
    assert env["RUNEFOBLE_WATCHER_PROPOSAL_TIMEOUT_S"] == "2.0"
