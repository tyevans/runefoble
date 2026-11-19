---
id: '0845'
title: Gateway Permission Checks Follow One Rule
status: Refined
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds:
- PRD-0023
governing_stories:
- US-0065
target_release: 0.9.0
---

# TASK-0845: Gateway Permission Checks Follow One Rule

## Status
Refined

Source: refactor round 2026-11-18 (user approved).

## Summary
The design keeps permission checks in the owning service, and the gateway only forwards proxy routes (TASK-0436, TASK-0439, TASK-0444). Some gateway code still checks permissions (`gateway/api/src/gateway_api/auth.py` `require_zanzibar_permission`, used by `routers/analytics_views.py` and others), and several docs say the gateway checks every route. State one rule and make the code and docs follow it.

Rule: a proxy route forwards the caller token and does not check permissions; the owner checks. A composite route, which the gateway builds from several owner reads (for example the spectate view), checks the permission it needs at the gateway, because no single owner sees the whole response.

## Documentation & Architecture Review
- `docs/how-to/call-owning-services-through-the-gateway.md`, `docs/how-to/define-spicedb-zanzibar-permissions.md`, `docs/how-to/authenticate-with-zitadel-oidc.md`, `docs/how-to/manage-campaign-lifecycle-and-invites.md`, `docs/how-to/broadcast-obs-stream-overlay-and-cinematic-camera.md`, `docs/reference/fastmcp-gateway.md`, `docs/reference/ports-and-endpoints.md`, `docs/reference/architecture-overview.md`.
- `gateway/api/src/gateway_api/main.py` module docstring, `gateway/api/src/gateway_api/routers/characters_subresources_proxy.py`.
- ADR-0001 (SpiceDB), ADR-0015.

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0065-game-session-lobby-readiness-and-launch.md`](../../user_stories/accepted/us-0065-game-session-lobby-readiness-and-launch.md)

## Detailed Specification & Implementation Plan
1. List every gateway route that calls `require_zanzibar_permission` or another SpiceDB check. For each, record proxy or composite, and whether the owner checks the same permission (cite file:line).
2. For a proxy route whose owner checks the same permission, remove the gateway check. Keep the gateway check on composite routes.
3. Write the rule in `docs/how-to/call-owning-services-through-the-gateway.md` and the architecture overview. Correct every doc and docstring above that contradicts it.

## Detailed Specification & Implementation Plan

Refactor round 2 addendum (2026-11-18): Also: `gateway/api/src/gateway_api/websocket_validator.py:87-103` applies an action permission policy to campaign socket frames. This is a proxy-route permission check and falls under the rule in this task. TASK-0846 makes the owner the checker.

## Frontdoor Test Plan
For each route whose gateway check is removed: a caller without the permission still gets 403, now from the owner, through the gateway (existing or new test in `gateway/api/tests/`).

## INVEST Criteria Evaluation
Small to medium. Testable through the gateway routes.

## Definition of Done
1. The route list is in the task report. 2. Code and docs follow the rule. 3. 403 tests pass. 4. `make health-check` passes.
