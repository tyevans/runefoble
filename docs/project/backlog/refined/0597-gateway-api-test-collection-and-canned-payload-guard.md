---
id: '0597'
title: Gateway API Test Collection and Canned Payload Guard
status: Refined
created: 2026-11-17
dependencies:
- TASK-0580
- TASK-0585
- TASK-0588
- TASK-0589
- TASK-0591
governing_adrs:
- ADR-0010
- ADR-0014
governing_prds:
- PRD-0023
governing_stories:
- US-0013
severity: medium
source_audits:
- w1-gateway-api.md
- w3-ddd-architecture.md
- w1-gates-python.md
target_release: 0.9.0
---

# TASK-0597: Gateway API Test Collection and Canned Payload Guard

## Status
Refined

## Summary
`uv run pytest gateway/api` exits with code 5 ("no tests ran"). The gateway tests live in the root `tests/` folder. Make the gateway tests collectable from the package, and add a guard that fails the build when a canned payload or in-memory fallback returns to `gateway/api/src`. Run this task after the proxy tasks merge, because those tasks rewrite the tests.

## Problem Statement
- `uv run pytest gateway/api -q` exits 5 (`w1-gateway-api.md` Commands run). `gateway/api` has no `tests/` folder.
- The tests that cover the gateway are in the root `tests/` folder. Examples: `test_gateway_api.py`, `test_gateway.py`, `test_blackbox_gateway_*.py` (13 files).
- `tests/test_gateway_api.py:39` asserts the canned string `"Valeros stepped forward"`. `tests/test_blackbox_gateway_hub_views.py:97` asserts the fallback title `"Sunken Citadel"` (`w3-ddd-architecture.md` F21).
- No test prevents a canned string from returning. The problem reached production because nothing failed.

## Documentation & Architecture Review
- ADR-0010: the CI pipeline runs `uv run pytest` across all bounded contexts. The gateway tests must be in that run.
- ADR-0014: frontdoor blackbox tests use public routes only. Setup goes through public routes. Do not write tuples or store state in tests.
- `AGENTS.md` Hard Invariant 7 and DoD item 5 apply to every moved test.
- `make test` is the developer entry point (`docs/reference/cli-interfaces.md`). Check the target before editing.

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0013-gateway-zanzibar-authorization.md`](../../user_stories/accepted/us-0013-gateway-zanzibar-authorization.md)

## Detailed Specification & Implementation Plan
1. Create `gateway/api/tests/` with a `conftest.py` that builds the gateway app and the owner ASGI apps. Use only public constructors.
2. Move the gateway-only test modules from `tests/` to `gateway/api/tests/`. Do not move a file that another open task rewrites. List the files moved and the files left in the PR.
3. Add `[tool.pytest.ini_options]` to `gateway/api/pyproject.toml` with `testpaths = ["tests"]`. Confirm `uv run pytest gateway/api` collects at least one test and exits 0.
4. Add `tests/test_canned_payload_guard.py` at the root. It reads every file under `gateway/api/src` and fails when any of these markers appears: `Valeros`, `Kyra`, `Sunken Citadel`, `Star-Eater`, `stepped forward`, `DEFAULT_BOARD_TOKENS`, `_proxy_or_fallback`, `proxy_or_fallback`, `except Exception:\n\s+pass`. Keep the marker list in the test file.
5. Remove the assertions listed in the Problem Statement. Do not replace them with a copy of the canned value.
6. Add a `make test-gateway` target that runs `uv run pytest gateway/api`. Document it in `docs/reference/cli-interfaces.md`.

## Frontdoor Blackbox Test Plan
- `gateway/api/tests/test_collection_smoke.py`: one test that calls `GET /healthz` through the public app. It proves collection works.
- `tests/test_canned_payload_guard.py`: fails when a marker is added to `gateway/api/src`. The test must fail when a marker is inserted in a temporary copy of one file (write the copy to `tmp_path`, not to the tracked tree).

| Case | Expected before fix | Expected after fix |
|---|---|---|
| `uv run pytest gateway/api` exit code | Fails: 5 | Passes: 0 |
| Guard test with a marker in a temp copy | Not present | Fails as designed |
| Guard test on the real tree | Not present | Passes |

## Definition of Done
1. `uv run pytest gateway/api` exits 0 and collects the moved tests.
2. `uv run pytest` at the root still passes.
3. `tests/test_canned_payload_guard.py` passes on the real tree.
4. No gateway test asserts a canned or fallback value.
5. `make test-gateway` exists and is documented.
6. `uv run ruff check .` passes.
