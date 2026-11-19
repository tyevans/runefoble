---
id: '0889'
title: Players Take a Lobby Seat Through the Gateway and the App Shell
status: Refined
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0013
- ADR-0014
- ADR-0015
governing_prds: []
governing_stories:
- US-0065
target_bc: game_session
target_release: 0.9.0
---

# TASK-0889: Players Take a Lobby Seat Through the Gateway and the App Shell

## Status

Refined. Found by TASK-0840 (`.audit/work/0840.md`).

## Summary

No player can take a seat in a session lobby. game_session has `POST /api/v1/sessions/{session_id}/join`, but the gateway does not expose it, and the lobby component and the App Shell never call it. Every lobby has an empty roster, so the US-0065 readiness and stand-in flows cannot happen in the product.

## Problem Statement

- `services/game_session/src/game_session/routers/session.py:88`: `join_session` seats the verified caller. It is the only join route.
- `gateway/api/src/gateway_api/routers/sessions_proxy.py`: no `/join` proxy route.
- `services/game_session/ui/src/lobby/runefoble-session-lobby.ts`: no join action.
- `e2e/features/session_lobby_roles.feature`: the readiness scenario can only check an empty lobby.

## Documentation & Architecture Review

- Gateway rule (TASK-0845, `docs/how-to/call-owning-services-through-the-gateway.md`): a proxy route forwards the token, and the owner checks the permission.
- ADR-0013: the join control is in the game_session lobby microfrontend, verified in Storybook.

## Product & User Story References

- US-0065: players join the lobby, toggle readiness, and the DM launches.

## Detailed Specification & Implementation Plan

1. Add `POST /api/v1/sessions/{session_id}/join` to `sessions_proxy.py`. It forwards the token and the body. game_session checks the permission. Register it in the OpenAPI docs and `docs/reference/ports-and-endpoints.md`.
2. The lobby component shows "Take a Seat" for a campaign player who is not seated (capability from the server reply, not a client role check). It emits an event; the App Shell view calls the gateway route and refreshes the roster.
3. The DM does not take a seat and is not counted (current rule).
4. Storybook story for the seated and unseated states.

## Frontdoor Blackbox Test Plan

- Gateway blackbox test: a campaign player joins through the gateway route and appears in `GET /api/v1/sessions/{id}`. A stranger gets the owner's 403. Unreachable owner gives 503.
- Playwright (`session_lobby_roles.feature`): a player opens the lobby, takes a seat, and the summary reads "0 of 1 players ready". The player toggles ready, and the summary reads "1 of 1 players ready". Setup through the campaign invite route only.

## Definition of Done

- Tests above pass. Docs and CHANGELOG `Added` entry.

## Audit Provenance

- Severity: high
- Source audits: .audit/work/0840.md
