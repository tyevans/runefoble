---
id: '0529'
title: Services Verify Zitadel Tokens (game_session, the_watcher, and Inference Worker Service Token)
status: Complete
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0536
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0005
- ADR-0007
governing_prds:
- PRD-0001
- PRD-0002
- PRD-0014
governing_stories:
- US-0013
target_release: 0.9.0
severity: critical
source_audits:
- w1-game-session.md
- w1-the-watcher.md
- w2-inference-worker.md
- w3-authz-coverage.md
---

# TASK-0529: Services Verify Zitadel Tokens (game_session, the_watcher, and Inference Worker Service Token)

## Status
Complete

## Summary
Game session and The Watcher take identity from `x-user-id`. Some checks run only when the header exists. The hot-swap route skips authorization without the header. The Inference Worker accepts any caller on all interfaces. Apply the verified principal to both services, and protect the Inference Worker with a service token from a secret.

## Problem Statement
- `services/game_session/src/game_session/routers/session.py:116` runs the hot-swap check only `if x_user_id:`. Audit w1-game-session F7.
- `game_session/routers/campfire.py:58`, `stronghold.py:68,98`, and the settlement routers check only `if x_user_id and not ...`. Audit w3-authz F10 (identity part).
- `services/the_watcher/src/the_watcher/dependencies.py` and five `the_watcher` modules read `x-user-id`. The copilot routes fail closed, but only when a user id exists. Audit w1-the-watcher and w3-authz F16 (identity part).
- `services/inference_worker/src/inference_worker/api.py:90-123` (`/inference/v1/intent`, `/dm-narration`, `/stand-in-action`) has no authentication. `config.py:19` binds `0.0.0.0`. CORS allows all origins with credentials (`api.py:67-73`). Audit w2-inference-worker F10.

## Documentation & Architecture Review
- Game session and The Watcher verify the user token the same way as TASK-0527. The gateway forwards the token (TASK-0536).
- Inference Worker is server-to-server. It does not need a user token. It needs a service credential. A shared secret from a Kubernetes Secret is the decision for this task. Zitadel machine-user client credentials are the alternative. Record the choice in the how-to. See the index report.
- `game_session` tuples for `game_session` type are never written. That is an authorization defect (audit w1-game-session F7). Out of scope.

## Product & User Story References
- PRD-0001 (The Watcher), PRD-0002 (stand-in), PRD-0014 (downtime and stronghold). US-0013.

## Detailed Specification & Implementation Plan
1. **game_session**: add the platform settings. Apply `require_principal` to every router. Delete every `if x_user_id` and `if x_user_id and not ...` guard. Delete `x_user_id` header parameters.
2. **the_watcher**: the same. Apply the identity dependency to all routers, including `copilot`, `intent`, `factions`, `stand_in`, and `autonomous_dm`.
3. **Inference Worker**
   - Require `Authorization: Bearer <service token>` on every `/inference/v1/*` route. Compare with `hmac.compare_digest`.
   - The token comes from `RUNEFOBLE_INFERENCE_SERVICE_TOKEN`. There is no default. The service refuses to start when it is unset.
   - The_watcher sends the token from its own settings. Add it to the outbound client.
   - Restrict CORS to the_watcher origin, or remove CORS. The caller is server-to-server.
4. Helm: add the service token as a secret reference for `inference-worker` and `the-watcher`. Coordinate with TASK-0626 (Kubernetes Secret for credentials).
5. Delete all `x-user-id` reads in these two services. Confirm with grep.

## Frontdoor Blackbox Test Plan
HTTP tests through `TestClient` and `httpx` for the Inference Worker.
- Before: `POST /hot-swap` without `x-user-id` returns 200. `POST /inference/v1/intent` with no token returns 200.
- After:
  - Hot-swap with no bearer returns 401. With a bearer and a forged `x-user-id` the acting user is the token subject.
  - Every `the_watcher` mutating route returns 401 without a bearer.
  - Inference Worker returns 401 without the service token and 200 with it.
  - Inference Worker refuses to start with no service token configured (process exit check).

## Definition of Done
1. `grep -rn "x_user_id\|x-user-id" services/game_session services/the_watcher services/inference_worker --include=*.py` returns no production matches.
2. Suites pass for both services. The_watcher to inference call works in the test stack with the service token.
3. Helm renders the secret reference and the variables.
4. `docs/how-to/authenticate-with-zitadel-oidc.md` gains a section on service-to-service tokens.
5. No file exceeds 500 lines. The copilot routers stay in their own modules.

## Orchestrator Addenda (2026-11-17, round 2)

Source: `.audit/synth/discovered-round2.md`.

- services/game_session/src/game_session/settlement/auth/tokens.py holds the game_session verifier singleton. Move it to a game_session identity module (no re-export) and update the callers.
