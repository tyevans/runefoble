"""Test seam over the single shared SpiceDB client factory.

Every gateway and library caller reads `runefoble_auth.factory.get_spicedb_client()`. A test
swaps the factory cache with this helper. The swap replaces the SpiceDB process boundary only.
It never patches a caller module, so every caller sees the same client.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0014: BDD Gherkin User Stories and Playwright E2E
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import runefoble_auth.factory as spicedb_factory


def shared_spicedb_client(client: Any) -> Any:
    """Return a patch that makes `client` the factory client until the patch stops.

    Use it as a context manager (`with shared_spicedb_client(db): ...`) or call
    `start()` and `stop()` in a fixture.
    """
    return patch.object(spicedb_factory, "_client", client)
