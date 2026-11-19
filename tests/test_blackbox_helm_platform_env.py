"""Blackbox checks for the platform environment that the Helm chart gives every service.

The tests render the umbrella chart with `helm template` and read only the public manifest
output. They check the variable names and values that each service container receives. They
do not read the templates. The same settings come from one helper, so a change to a platform
host or port shows up here for every service at once (TASK-0725).
"""

import pytest

from tests.helpers.helm import render_chart

PASSWORD_REF = {
    "name": "POSTGRES_PASSWORD",
    "secret": "runefoble-credentials",
    "key": "postgres-password",
}

# Services that read the shared platform settings. The first four are Node or Python workers
# with their own container, and game-session is a Python service that uses the default driver.
PLATFORM_SERVICES = [
    "audience-studio",
    "soundscape",
    "campaign-analytics",
    "asset-forge",
    "game-session",
]

# Only audience-studio keeps a plain postgresql:// URL, because its driver does not use asyncpg.
DRIVER_BY_SERVICE = {"audience-studio": "postgresql"}

SHARED_VALUES = {
    "RUNEFOBLE_SPICEDB_ENDPOINT": "spicedb:50051",
    "RUNEFOBLE_REDIS_URL": "redis://runefoble-redis:6379/0",
    "RUNEFOBLE_OTEL_ENABLED": "true",
    "RUNEFOBLE_OTEL_EXPORTER_OTLP_ENDPOINT": "http://otel-collector:4317",
    "RUNEFOBLE_ZITADEL_ISSUER": "http://auth.localhost",
    "RUNEFOBLE_ZITADEL_INTERNAL_URL": "http://zitadel:8080",
}


def _containers(docs: list[dict]) -> dict[str, dict]:
    """Return {container name: {env name: env entry}} for every Deployment container."""
    result: dict[str, dict] = {}
    for doc in docs:
        if doc.get("kind") != "Deployment":
            continue
        for container in doc["spec"]["template"]["spec"]["containers"]:
            result[container["name"]] = {item["name"]: item for item in container.get("env", [])}
    return result


def _value(env: dict[str, dict], name: str) -> str | None:
    entry = env.get(name)
    return None if entry is None else entry.get("value")


def _secret_ref(env: dict[str, dict], name: str) -> tuple[str, str] | None:
    entry = env.get(name)
    if entry is None or "valueFrom" not in entry:
        return None
    ref = entry["valueFrom"]["secretKeyRef"]
    return ref["name"], ref["key"]


@pytest.fixture(scope="module")
def default_env() -> dict[str, dict]:
    return _containers(render_chart())


@pytest.mark.parametrize("service", PLATFORM_SERVICES)
def test_platform_service_receives_the_shared_platform_values(default_env, service):
    """Each platform service gets the same host, port, and Zitadel values from the one helper."""
    env = default_env[service]

    expected_scheme = DRIVER_BY_SERVICE.get(service, "postgresql+asyncpg")
    assert _value(env, "RUNEFOBLE_DATABASE_URL") == (
        f"{expected_scheme}://runefoble_user:$(POSTGRES_PASSWORD)@postgres:5432/runefoble"
    )
    for name, expected in SHARED_VALUES.items():
        assert _value(env, name) == expected, f"{service} {name}"


@pytest.mark.parametrize("service", PLATFORM_SERVICES)
def test_platform_service_reads_its_secrets_from_the_credentials_secret(default_env, service):
    """POSTGRES_PASSWORD and the SpiceDB key come from the chart Secret, never as literal values."""
    env = default_env[service]

    assert _secret_ref(env, "POSTGRES_PASSWORD") == ("runefoble-credentials", "postgres-password")
    assert _secret_ref(env, "RUNEFOBLE_SPICEDB_PRESHARED_KEY") == (
        "runefoble-credentials",
        "spicedb-preshared-key",
    )
    assert _value(env, "POSTGRES_PASSWORD") is None
    assert _value(env, "RUNEFOBLE_SPICEDB_PRESHARED_KEY") is None


def test_database_url_reads_the_password_before_it_is_expanded(default_env):
    """The password is expanded by Kubernetes, so POSTGRES_PASSWORD must come first in the env list."""
    for service in PLATFORM_SERVICES:
        names = list(default_env[service])
        assert names.index("POSTGRES_PASSWORD") < names.index("RUNEFOBLE_DATABASE_URL"), service


def test_service_specific_toggles_still_apply(default_env):
    """Per-service keys still decide the optional variables. The shared helper does not override them."""
    # game-session keeps the default environment and Silo endpoint.
    assert _value(default_env["game-session"], "RUNEFOBLE_ENVIRONMENT") == "local"
    assert _value(default_env["game-session"], "RUNEFOBLE_SILO_ENDPOINT") == "silo:9000"
    assert _value(default_env["game-session"], "RUNEFOBLE_EVENT_STORE_BACKEND") == "postgresql"

    # audience-studio sets environment and siloEndpoint to false in values.yaml.
    assert "RUNEFOBLE_ENVIRONMENT" not in default_env["audience-studio"]
    assert "RUNEFOBLE_SILO_ENDPOINT" not in default_env["audience-studio"]
    assert _value(default_env["audience-studio"], "RUNEFOBLE_EVENT_STORE_BACKEND") == "postgresql"


def test_redis_url_is_rendered_only_when_redis_is_enabled():
    """redis.enabled controls RUNEFOBLE_REDIS_URL on every service container."""
    disabled = _containers(render_chart("--set", "redis.enabled=false"))

    for service in PLATFORM_SERVICES:
        assert "RUNEFOBLE_REDIS_URL" not in disabled[service], service


def test_database_url_follows_the_postgres_port_value():
    """The PostgreSQL port in each URL comes from postgres.port, the same value as the Service."""
    env = _containers(render_chart("--set", "postgres.port=5433"))

    for service in PLATFORM_SERVICES:
        url = _value(env[service], "RUNEFOBLE_DATABASE_URL")
        assert url is not None and url.endswith("@postgres:5433/runefoble"), service
