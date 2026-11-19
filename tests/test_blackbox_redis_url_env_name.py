"""Blackbox checks that the Redis URL has one environment name, RUNEFOBLE_REDIS_URL (TASK-0839).

The tests use only public inputs: the environment read by `PlatformSettings`, the
host and port that the dev orchestrator resolves, and the manifests that
`helm template` renders. A variable named `REDIS_URL` must not change any of them.
"""

import pytest
from runefoble_platform.config import PlatformSettings

from scripts.dev_orchestrator.ports import DEFAULT_REDIS_URL, redis_endpoint
from tests.helpers.helm import render_chart

LEGACY_NAME = "REDIS_URL"
CURRENT_NAME = "RUNEFOBLE_REDIS_URL"


@pytest.fixture
def clean_redis_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    monkeypatch.delenv(CURRENT_NAME, raising=False)
    monkeypatch.delenv(LEGACY_NAME, raising=False)
    return monkeypatch


def test_settings_read_the_redis_url_from_runefoble_redis_url(
    clean_redis_env: pytest.MonkeyPatch,
) -> None:
    clean_redis_env.setenv(CURRENT_NAME, "redis://redis-current:6390/3")

    assert str(PlatformSettings().redis_url) == "redis://redis-current:6390/3"


def test_settings_ignore_a_redis_url_variable_without_the_prefix(
    clean_redis_env: pytest.MonkeyPatch,
) -> None:
    clean_redis_env.setenv(LEGACY_NAME, "redis://legacy-only:6379/0")

    assert str(PlatformSettings().redis_url) == "redis://localhost:6379/0"


def test_dev_orchestrator_ignores_a_redis_url_variable_without_the_prefix() -> None:
    env = {LEGACY_NAME: "redis://legacy-only:6391/0"}

    assert redis_endpoint(env) == ("localhost", 6379)
    assert DEFAULT_REDIS_URL == "redis://localhost:6379/0"


def test_dev_orchestrator_reads_the_prefixed_name() -> None:
    env = {CURRENT_NAME: "redis://current-host:6391/0", LEGACY_NAME: "redis://legacy-only:6379/0"}

    assert redis_endpoint(env) == ("current-host", 6391)


def _rendered_env_by_container() -> dict[str, dict[str, str]]:
    docs = render_chart()
    result: dict[str, dict[str, str]] = {}
    for doc in docs:
        if doc.get("kind") != "Deployment":
            continue
        for container in doc["spec"]["template"]["spec"]["containers"]:
            env = container.get("env", [])
            result[container["name"]] = {item["name"]: item.get("value", "") for item in env}
    return result


def test_helm_renders_the_prefixed_redis_url_and_no_legacy_name() -> None:
    env_by_container = _rendered_env_by_container()

    consumers = {name: env for name, env in env_by_container.items() if CURRENT_NAME in env}
    assert consumers, "no container renders RUNEFOBLE_REDIS_URL"
    for name, env in env_by_container.items():
        assert LEGACY_NAME not in env, f"{name} still renders {LEGACY_NAME}"
