"""Child-process entry for the Redis container reaping blackbox test. It is not a suite module.

The blackbox test runs this file in a child pytest process. The child starts a Redis container
through `redis_container` and writes the container name to `RUNEFOBLE_HOLD_INFO_FILE`. Then it
waits until the parent kills it, so the container's teardown never runs.
"""

from __future__ import annotations

import json
import os
import time

from tests.helpers.ports import free_port
from tests.helpers.redis_container import redis_container


def test_hold_redis_container():
    port = free_port()
    with redis_container(port):
        info_path = os.environ["RUNEFOBLE_HOLD_INFO_FILE"]
        temp_path = f"{info_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump({"container_name": f"runefoble-redis-test-{port}"}, handle)
        os.replace(temp_path, info_path)
        while True:
            time.sleep(1)
