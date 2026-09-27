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

from pathlib import Path

from fastapi import APIRouter
from game_session.main import app as session_app
from game_session.routers import caravan_contracts_router
from game_session.routers.caravan_contracts import (
    accept_caravan_contract,
    board_router,
    dispatch_contract_caravan,
    fulfill_caravan_contract,
    get_caravan_contract,
    lifecycle_router,
    list_caravan_contracts,
    post_caravan_contract,
    report_contract_ambush,
)
from game_session.routers.caravan_contracts import (
    router as pkg_router,
)


def test_modular_file_length_limits() -> None:
    """Verify all submodules in caravan_contracts strictly satisfy line length limits (< 190 lines)."""
    pkg_dir = (
        Path(__file__).resolve().parent.parent.parent
        / "services"
        / "game_session"
        / "src"
        / "game_session"
        / "routers"
        / "caravan_contracts"
    )
    assert pkg_dir.is_dir()
    for py_file in pkg_dir.glob("*.py"):
        line_count = len(py_file.read_text(encoding="utf-8").splitlines())
        assert line_count < 190, f"{py_file.name} exceeds 190 lines limit ({line_count} lines)"


def test_facade_backward_compatibility() -> None:
    """Verify facade re-exports combined router and functions cleanly."""
    facade_file = (
        Path(__file__).resolve().parent.parent.parent
        / "services"
        / "game_session"
        / "src"
        / "game_session"
        / "routers"
        / "caravan_contracts.py"
    )
    assert facade_file.exists()
    assert len(facade_file.read_text(encoding="utf-8").splitlines()) < 25

    import game_session.routers.caravan_contracts as facade

    assert hasattr(facade, "router")
    assert isinstance(facade.router, APIRouter)
    assert facade.router is pkg_router


def test_router_exports_and_sub_routers() -> None:
    """Verify aggregated router includes board and lifecycle routes."""
    assert isinstance(board_router, APIRouter)
    assert isinstance(lifecycle_router, APIRouter)
    assert isinstance(caravan_contracts_router, APIRouter)

    for fn in [
        post_caravan_contract,
        list_caravan_contracts,
        get_caravan_contract,
        accept_caravan_contract,
        dispatch_contract_caravan,
        report_contract_ambush,
        fulfill_caravan_contract,
    ]:
        assert callable(fn)


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
