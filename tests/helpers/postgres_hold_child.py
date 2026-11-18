"""Child-process entry for the container reaping blackbox test. It is not a suite module.

The blackbox test runs this file in a child pytest process. The child requests the
`postgres_service` fixture and writes the container name to `RUNEFOBLE_HOLD_INFO_FILE`.
Then it does one of two things, chosen by `RUNEFOBLE_HOLD_MODE`:
- `hold`: waits until the parent kills it, so fixture teardown never runs.
- `exit`: returns, so fixture teardown runs and removes the container.
"""

from __future__ import annotations

import json
import os
import time


def test_hold_postgres_container(postgres_service):
    if postgres_service is None:
        raise RuntimeError("postgres_service yielded None: the container did not start")
    info_path = os.environ["RUNEFOBLE_HOLD_INFO_FILE"]
    temp_path = f"{info_path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump({"container_name": postgres_service["container_name"]}, handle)
    os.replace(temp_path, info_path)
    if os.environ["RUNEFOBLE_HOLD_MODE"] == "hold":
        while True:
            time.sleep(1)
