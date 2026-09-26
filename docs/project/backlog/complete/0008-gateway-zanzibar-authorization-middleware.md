# TASK-0008: Gateway SpiceDB Zanzibar Authorization Middleware

## Status
Complete

## Summary
Integrated fine-grained SpiceDB Zanzibar object authorization into `gateway/api` without hardcoded role strings in application logic. Added `require_zanzibar_permission` dependency checking permissions against Zanzibar relationships (`run_session`, `view`, `owner`, `dungeon_master`, `player`), protected campaign and session endpoints with structured 403 Forbidden rejection diagnostics, and created unit tests in `tests/test_gateway_auth.py`.

## Key Changes
- `gateway/api/pyproject.toml`:
  - Added workspace dependency `"runefoble-auth"`.
- `gateway/api/src/gateway_api/auth.py`:
  - Implemented `require_zanzibar_permission` FastAPI dependency factory verifying subject permissions against SpiceDB Zanzibar schema.
  - Returns structured 403 Forbidden error with diagnostic context upon rejection.
- `gateway/api/src/gateway_api/main.py`:
  - Added `/api/v1/campaigns/{campaign_id}/roles` endpoint to assign Zanzibar relationship tuples dynamically.
  - Protected session and board endpoints (`/api/v1/sessions/{session_id}`, `/api/v1/boards/{session_id}`) with `view` permission checks.
  - Protected turn advancement (`/api/v1/sessions/{session_id}/turns/advance`) with `run_session` permission checks.
  - Kept file clean and modular (222 lines, well below 500 limit).
- `tests/test_gateway_auth.py`:
  - Added unit tests verifying permission rejection, role assignment, player access, and DM turn advancement.

## Verification
- `uv run pytest`: 79/79 tests passed.
- `uv run ruff check .` & `uv run ruff format .`: Clean.
