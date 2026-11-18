"""The Helm chart loads the same SpiceDB schema that the services check against (ADR-0001).

Helm can read files only inside the chart, so the chart holds a copy of
`libs/runefoble_auth/schema/runefoble.zed`. The rendered schema job must carry that schema
exactly. A stale copy makes every permission check in Kind use an old schema.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_SCHEMA = REPO_ROOT / "libs" / "runefoble_auth" / "schema" / "runefoble.zed"
CHART = REPO_ROOT / "deployments" / "helm" / "runefoble"


def test_rendered_schema_job_carries_the_service_schema() -> None:
    rendered = subprocess.run(
        ["helm", "template", "runefoble", str(CHART)],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    ).stdout
    schemas = [
        doc["data"]["runefoble.zed"]
        for doc in yaml.safe_load_all(rendered)
        if doc and doc.get("kind") == "ConfigMap" and "runefoble.zed" in doc.get("data", {})
    ]
    assert len(schemas) == 1, f"expected one schema ConfigMap, found {len(schemas)}"
    assert schemas[0].strip() == SOURCE_SCHEMA.read_text().strip(), (
        "deployments/helm/runefoble/files/runefoble.zed differs from the service schema. "
        "Copy libs/runefoble_auth/schema/runefoble.zed into the chart."
    )
