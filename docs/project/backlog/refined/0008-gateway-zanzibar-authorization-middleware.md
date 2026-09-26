# TASK-0008: Gateway SpiceDB Zanzibar Authorization Middleware

## Description
Integrate fine-grained SpiceDB Zanzibar checks into `gateway/api` using `libs/runefoble_auth/spicedb.py`. Enforce object-level permissions (`run_session`, `play`, `view`, `edit`) across campaigns and sessions without any hardcoded role strings in application routing.

## Governing Documents
- ADRs: ADR-0001, ADR-0005, ADR-0007
- PRDs: PRD-0001
- User Stories: US-0009, US-0013

## Definition of Done
1. `gateway/api` provides a dependency or middleware checking permissions via `SpiceDBClient`.
2. Endpoints requiring DM permissions (`/api/v1/sessions/{id}/turns/advance`, `/api/v1/campaigns/{id}/mutate`) verify `run_session` or `edit` permission for the caller's subject.
3. Requests with insufficient permissions return HTTP 403 Forbidden with diagnostic detail.
4. Unit tests in `tests/test_gateway_auth.py` verify allowed and rejected requests for DM, Player, and Spectator subjects.
5. All checks pass via `uv run pytest` and `uv run ruff check .`.
