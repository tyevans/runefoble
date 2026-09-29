---
id: '0442'
title: Dev Environment Blackbox Test Suite Modular Decomposition
status: Proposed
created: 2026-09-29
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

# TASK-0442: Dev Environment Blackbox Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_dev_environment.py` (328 lines, 65.6% of limit) into modular test submodules under `tests/test_blackbox_dev_environment/` (`test_cli_args.py`, `test_ports_and_sockets.py`, `test_gateway_proxy.py`, `test_process_lifecycle.py`), ensuring all test submodules remain strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_dev_environment.py` exercises Makefile targets, CLI parsing, TCP socket availability probing, health check polling, process lifecycle termination, and Vite proxy forwarding in a single 328-line file. As local development orchestration expands with additional services (e.g. Audience Studio, background workers, Spicedb cluster health), this test suite will rapidly breach the 500-line invariant limit unless modularized into focused test modules.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout and executable CLI tooling.
- **ADR-0010: Developer Experience & Tooling**: Reliable `make dev` local development loop and test verification.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 130 lines).

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
  - [`us-0001-developer-local-environment-setup.md`](../../user_stories/accepted/us-0001-developer-local-environment-setup.md)
  - [`us-0065-game-session-staging-lobby-and-pre-game-assembly.md`](../../user_stories/accepted/us-0065-game-session-staging-lobby-and-pre-game-assembly.md)

## Scope of Work
1. **Create Modular Test Directory (`tests/test_blackbox_dev_environment/`)**:
   - `test_cli_args.py`: Validate CLI flags, defaults, and Makefile dev targets (< 90 lines).
   - `test_ports_and_sockets.py`: Validate TCP socket checks and port open utilities (< 80 lines).
   - `test_process_lifecycle.py`: Validate process startup, health check polling, and graceful termination (< 100 lines).
   - `test_gateway_proxy.py`: Validate Vite proxy gateway routing and health checks (< 90 lines).
2. **Aggregator Shim (`tests/test_blackbox_dev_environment.py`)**:
   - Re-export test functions or delegate to sub-suite maintaining backwards compatibility (< 30 lines).
3. **Verification**:
   - Run `uv run pytest tests/test_blackbox_dev_environment/` and assert all tests pass.

## Definition of Done
1. `tests/test_blackbox_dev_environment.py` decomposed into modular sub-suites strictly < 120 lines each.
2. All dev environment blackbox tests pass with 100% assertions.
3. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
