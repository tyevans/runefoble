"""Blackbox checks for the hosted Secret contract (TASK-0959).

The tests read two public outputs only: the rendered chart (`helm template`) and the
reference page `docs/reference/hosted-secrets.md`. The table on that page is the contract.
The tests check that the rendered chart reads exactly the keys that the table lists, from the
Secret that the operator names, and that the generated Secrets keep their chart names.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.helpers.helm import (
    CHART_DIR,
    helm_template_result,
    hosted_values_file,
    render_chart,
)

REPO_ROOT = CHART_DIR.parents[2]
CONTRACT_PAGE = REPO_ROOT / "docs" / "reference" / "hosted-secrets.md"
OPERATOR_NAME_CELL = "credentials.existingSecret"
CAMPAIGN_LORE_NAME_CELL = "services.campaignLore.embeddingApiKeySecret"
GENERATED_NAME_CELLS = {"zitadel-admin", "runefoble-zitadel-client"}
TEAM_SECRET = "team-credentials"


def _plain(cell: str) -> str:
    return cell.strip().strip("`").strip()


def _keys(cell: str) -> set[str]:
    return {_plain(part) for part in cell.split(",") if _plain(part)}


def _contract_rows() -> list[dict[str, str]]:
    """Return one dict per table row, keyed by the column header. Skips the separator row."""
    lines = CONTRACT_PAGE.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("| Secret name |"))
    headers = [_plain(cell) for cell in lines[start].strip().strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows.append(dict(zip(headers, cells, strict=True)))
    return rows


def _rows_named(name_cell: str) -> list[dict[str, str]]:
    return [row for row in _contract_rows() if _plain(row["Secret name"]) == name_cell]


def _contract_keys(name_cell: str) -> set[str]:
    return set().union(*(_keys(row["Key"]) for row in _rows_named(name_cell)))


def _env_secret_refs(docs: list[dict[str, Any]]) -> list[tuple[str, dict[str, str]]]:
    """Return (env var name, secretKeyRef) for every container env entry that reads a Secret."""
    refs: list[tuple[str, dict[str, str]]] = []
    for doc in docs:
        if doc.get("kind") not in {"Deployment", "Job", "StatefulSet", "DaemonSet"}:
            continue
        pod_spec = doc["spec"]["template"]["spec"]
        for container in pod_spec.get("initContainers", []) + pod_spec.get("containers", []):
            for item in container.get("env", []):
                ref = item.get("valueFrom", {}).get("secretKeyRef")
                if ref is not None:
                    refs.append((item["name"], ref))
    return refs


def _secret_names(docs: list[dict[str, Any]]) -> set[str]:
    return {doc["metadata"]["name"] for doc in docs if doc.get("kind") == "Secret"}


def test_contract_table_lists_the_keys_of_the_rendered_credential_secret():
    """The keys of the operator Secret in the table equal the keys the local render holds."""
    docs = render_chart()
    rendered = next(
        doc
        for doc in docs
        if doc.get("kind") == "Secret" and doc["metadata"]["name"] == "runefoble-credentials"
    )

    assert _contract_keys(OPERATOR_NAME_CELL) == set(rendered["stringData"])


def test_hosted_render_reads_only_contract_keys_from_the_named_secret(tmp_path: Path):
    """Every key that a hosted render reads from the operator Secret is in the table."""
    docs = render_chart(
        "-f",
        str(hosted_values_file(tmp_path, **{"credentials.existingSecret": TEAM_SECRET})),
    )
    read_from_team = {ref["key"] for _, ref in _env_secret_refs(docs) if ref["name"] == TEAM_SECRET}

    assert read_from_team == _contract_keys(OPERATOR_NAME_CELL)


def test_hosted_render_reads_no_credential_from_the_local_secret(tmp_path: Path):
    """A hosted render names the operator Secret for every credential and renders no local one."""
    docs = render_chart(
        "-f",
        str(hosted_values_file(tmp_path, **{"credentials.existingSecret": TEAM_SECRET})),
    )
    names = {ref["name"] for _, ref in _env_secret_refs(docs)}

    assert "runefoble-credentials" not in names
    assert "runefoble-credentials" not in _secret_names(docs)
    assert TEAM_SECRET not in _secret_names(docs)


def test_hosted_campaign_lore_reads_api_key_from_the_named_secret(tmp_path: Path):
    """The campaign-lore pod reads the api-key key. The chart renders no Secret with that name."""
    docs = render_chart("-f", str(hosted_values_file(tmp_path)))
    refs = dict(_env_secret_refs(docs))

    assert refs["RUNEFOBLE_EMBEDDING_API_KEY"] == {
        "name": "campaign-lore-embedding",
        "key": "api-key",
    }
    assert "campaign-lore-embedding" not in _secret_names(docs)


def test_campaign_lore_row_names_the_api_key_key():
    """The table row for the campaign-lore Secret lists the key api-key."""
    assert _contract_keys(CAMPAIGN_LORE_NAME_CELL) == {"api-key"}


def test_hosted_render_fails_without_a_campaign_lore_secret_name(tmp_path: Path):
    """An empty campaign-lore Secret name fails the hosted render and names the key path."""
    proc = helm_template_result(
        "-f",
        str(hosted_values_file(tmp_path, **{"services.campaignLore.embeddingApiKeySecret": ""})),
    )

    assert proc.returncode != 0
    assert "services.campaignLore.embeddingApiKeySecret" in proc.stderr


def test_generated_secret_rows_match_the_chart_values():
    """The two generated Secrets in the table use the names that the chart sets."""
    values = yaml.safe_load((CHART_DIR / "values.yaml").read_text(encoding="utf-8"))
    chart_names = {
        values["zitadel"]["bootstrap"]["adminSecret"],
        values["zitadel"]["client"]["secretName"],
    }

    table_names = {_plain(row["Secret name"]) for row in _contract_rows()} & GENERATED_NAME_CELLS

    assert table_names == chart_names == GENERATED_NAME_CELLS


@pytest.mark.parametrize(
    ("name_cell", "expected"),
    [
        ("zitadel-admin", {"pat"}),
        ("runefoble-zitadel-client", {"project-id", "client-id"}),
    ],
)
def test_generated_secret_rows_list_their_keys(name_cell: str, expected: set[str]):
    """Each generated Secret row lists the keys that its writer sets."""
    assert _contract_keys(name_cell) == expected


BACKUP_NAME_CELL = "backup.credentialsSecret"
TEAM_BACKUP_SECRET = "team-backup-credentials"
BACKUP_ENCRYPTION_KEY = "encryption-passphrase"


def _backup_secret_refs(docs: list[dict[str, Any]]) -> set[tuple[str, str]]:
    """Return (secret name, key) for every env entry of the backup CronJob and restore Job."""
    refs: set[tuple[str, str]] = set()
    for doc in docs:
        if doc.get("kind") == "CronJob":
            pod_spec = doc["spec"]["jobTemplate"]["spec"]["template"]["spec"]
        elif doc.get("kind") == "Job" and doc["metadata"]["name"] == "postgres-restore":
            pod_spec = doc["spec"]["template"]["spec"]
        else:
            continue
        for container in pod_spec.get("initContainers", []) + pod_spec.get("containers", []):
            for item in container.get("env", []):
                ref = item.get("valueFrom", {}).get("secretKeyRef")
                if ref is not None:
                    refs.add((ref["name"], ref["key"]))
    return refs


def test_backup_rows_list_the_keys_that_the_backup_reads_without_encryption(tmp_path: Path):
    """Without encryption, the backup and restore read access-key and secret-key only."""
    docs = render_chart(
        "-f",
        str(
            hosted_values_file(
                tmp_path,
                **{
                    "backup.credentialsSecret": TEAM_BACKUP_SECRET,
                    "restore.enabled": True,
                    "restore.objectPrefix": "postgres/2026-11-18",
                },
            )
        ),
    )

    read = {key for name, key in _backup_secret_refs(docs) if name == TEAM_BACKUP_SECRET}

    assert read == _contract_keys(BACKUP_NAME_CELL) - {BACKUP_ENCRYPTION_KEY}


def test_backup_rows_list_the_keys_that_the_backup_reads_with_encryption(tmp_path: Path):
    """With encryption, the backup and restore also read the passphrase key."""
    docs = render_chart(
        "-f",
        str(
            hosted_values_file(
                tmp_path,
                **{
                    "backup.credentialsSecret": TEAM_BACKUP_SECRET,
                    "backup.encryption.enabled": True,
                    "restore.enabled": True,
                    "restore.objectPrefix": "postgres/2026-11-18",
                },
            )
        ),
    )

    read = {key for name, key in _backup_secret_refs(docs) if name == TEAM_BACKUP_SECRET}

    assert read == _contract_keys(BACKUP_NAME_CELL)
    assert BACKUP_ENCRYPTION_KEY in read
