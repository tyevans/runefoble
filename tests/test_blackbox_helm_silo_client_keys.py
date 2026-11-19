"""Every service that writes to Silo gets the Silo keys from the credentials Secret (TASK-0926).

The Silo client signs each request with the keys. The keys have no default, so a service
without them cannot store an asset.
"""

from __future__ import annotations

import pytest

from tests.helpers.helm import render_chart

SILO_WRITERS = ["asset-forge", "board-state"]
KEY_ENV = {
    "RUNEFOBLE_SILO_ACCESS_KEY": "silo-access-key",
    "RUNEFOBLE_SILO_SECRET_KEY": "silo-secret-key",
}


def _service_env(name: str) -> dict[str, dict]:
    deployments = [
        doc
        for doc in render_chart()
        if doc.get("kind") == "Deployment" and doc["metadata"]["name"] == name
    ]
    assert len(deployments) == 1, name
    container = deployments[0]["spec"]["template"]["spec"]["containers"][0]
    return {item["name"]: item for item in container.get("env", [])}


@pytest.mark.parametrize("service", SILO_WRITERS)
def test_silo_writer_reads_the_silo_keys_from_the_secret(service: str) -> None:
    env = _service_env(service)
    for var, secret_key in KEY_ENV.items():
        assert var in env, f"{service} lacks {var}"
        assert env[var]["valueFrom"]["secretKeyRef"]["key"] == secret_key
        assert "value" not in env[var]
