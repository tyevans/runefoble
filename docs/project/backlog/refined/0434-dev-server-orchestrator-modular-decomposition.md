---
id: '0434'
title: Dev Server Orchestrator Modular Decomposition
status: Refined
created: 2026-09-28
dependencies:
- TASK-0352
governing_adrs:
- ADR-0003
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0001
- US-0065
target_release: 0.9.0
---

# TASK-0434: Dev Server Orchestrator Modular Decomposition

## Status
Refined

## Summary
Decompose `scripts/dev_server.py` (411 lines, 82.2% of limit) into modular utility submodules under `scripts/dev_orchestrator/` (`ports.py`, `runner.py`, `health.py`, `colors.py`), ensuring `scripts/dev_server.py` serves as a clean, high-level CLI driver strictly < 100 lines per Hard Invariant 6.

## Problem Statement
`scripts/dev_server.py` implements local development orchestration for the entire Runefoble platform. It currently bundles ANSI color formatting, TCP socket probing, SpiceDB automatic kubectl port-forwarding, background service process management, subprocess stdout/stderr line streaming with prefixed labels, hot-reloading Vite frontend startup, health check polling, and graceful multi-signal handling into a monolithic 411-line script. As new downstream services and diagnostic checks are added, this file will breach the 500-line invariant limit unless decomposed into dedicated submodules.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/tutorials/01-local-development-setup.md`: Local development workflow, ports, and service startup.
  - `docs/reference/ports-and-endpoints.md`: Standard ports (Gateway 8000, Vite 5173, SpiceDB 50051).
- **Governing Architecture & ADRs**:
  - **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout and executable CLI tooling.
  - **ADR-0010: Developer Experience & Tooling**: Reliable `make dev` local development loop.
  - **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 130 lines).

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
  - [`us-0001-developer-local-environment-setup.md`](../../user_stories/accepted/us-0001-developer-local-environment-setup.md)
  - [`us-0065-game-session-staging-lobby-and-pre-game-assembly.md`](../../user_stories/accepted/us-0065-game-session-staging-lobby-and-pre-game-assembly.md)

## Detailed Specification & Implementation Plan
1. **ANSI Colors & Formatting (`scripts/dev_orchestrator/colors.py`)**:
   - Extract ANSI terminal color constants (`CYAN`, `GREEN`, `YELLOW`, `RED`, `MAGENTA`, `BOLD`, `RESET`) (< 30 lines).
2. **Port Probing & Forwarding (`scripts/dev_orchestrator/ports.py`)**:
   - Extract `is_port_open` and `ensure_spicedb_available` with kubectl port-forward fallback (< 70 lines).
3. **Health Checking & Gating (`scripts/dev_orchestrator/health.py`)**:
   - Extract `wait_for_gateway_healthy` with configurable timeout and error reporting (< 60 lines).
4. **Process Management & Stream Pipe (`scripts/dev_orchestrator/runner.py`)**:
   - Extract `pipe_stream`, `DevService` model, and `DevProcessManager` handling subprocess lifecycles, signal dispatch (`SIGINT`, `SIGTERM`), and clean teardown (< 120 lines).
5. **CLI Driver Facade (`scripts/dev_server.py`)**:
   - Retain argument parsing, orchestrator assembly, and main entrypoint as a concise CLI facade (< 70 lines).
6. **Blackbox Verification**:
   - Run `python3 tests/test_blackbox_dev_environment.py` and `python3 scripts/dev_server.py --help` asserting identical behavior and argument contracts.

## INVEST Criteria Evaluation
- **Independent (I)**: Refactoring of developer script that preserves all CLI arguments and behavior.
- **Negotiable (N)**: Submodule naming can be refined.
- **Valuable (V)**: Eliminates file size invariant risk (>400 lines) and improves maintainability of core developer loop.
- **Estimable (E)**: Pure refactoring with existing test suite coverage.
- **Small (S)**: Confined to `scripts/dev_server.py` and new `scripts/dev_orchestrator/` package.
- **Testable (T)**: Tested with existing `test_blackbox_dev_environment.py`.

## Definition of Done
1. `scripts/dev_server.py` reduced to strictly < 100 lines.
2. Extracted submodules under `scripts/dev_orchestrator/` strictly < 130 lines each.
3. `python3 scripts/dev_server.py --help` runs without import errors.
4. `uv run pytest tests/test_blackbox_dev_environment.py` passes with 100% assertions.
5. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
