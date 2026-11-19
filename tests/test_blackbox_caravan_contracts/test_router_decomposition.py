"""Tests verifying modular decomposition and backward compatibility of caravan_contracts router.

Governed by:
- ADR-0001: Fine-Grained Authorization with SpiceDB Zanzibar
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0006: Redis Streams Distributed Event Bus
- ADR-0011: eventsource-py Core Event Sourcing
- Hard Invariant 6: File length limit (< 500 lines, all submodules < 180 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
- TASK-0147: Caravan Contracts API Router Modular Decomposition
"""

from __future__ import annotations

from tests.helpers.game_session_app import session_app


def test_routes_registered_in_session_app() -> None:
    """Verify all caravan contract endpoints are mounted in session_app."""
    paths = session_app.openapi()["paths"]
    expected = {
        "/api/v1/shared-worlds/{shared_world_id}/caravans/contracts",
        "/api/v1/shared-worlds/{shared_world_id}/caravans/contracts/{contract_id}",
        "/api/v1/shared-worlds/{shared_world_id}/caravans/contracts/{contract_id}/accept",
        "/api/v1/shared-worlds/{shared_world_id}/caravans/contracts/{contract_id}/dispatch",
        "/api/v1/shared-worlds/{shared_world_id}/caravans/contracts/{contract_id}/ambush",
        "/api/v1/shared-worlds/{shared_world_id}/caravans/contracts/{contract_id}/fulfill",
    }
    for path in expected:
        assert path in paths, f"Missing route {path} in session_app OpenAPI"
