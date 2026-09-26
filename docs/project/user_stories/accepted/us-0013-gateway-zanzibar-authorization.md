---
id: 0013
title: Zanzibar Campaign Role Authorization Gateway Enforcement
status: Accepted
created: 2026-09-25
governing_prd: PRD-0013
---

# US-0013: Zanzibar Campaign Role Authorization Gateway Enforcement

## Governing PRD
- [`PRD-0013: Immersive & Intuitive Frontend Experience with Tactile Board Kinematics`](../../product/accepted/prd-0013-immersive-and-intuitive-frontend-experience.md)

## Persona
Evelyn (Human DM) / Alex (Developer)

## User Story
As a DM or platform developer,
I want the API Gateway to enforce fine-grained SpiceDB Zanzibar checks against campaign resources (`run_session`, `play`, `view`),
So that players cannot unilaterally mutate DM tokens or access campaign master states, while ensuring zero role checks are hardcoded in business logic.

## Acceptance Criteria
1. Gateway requests inspect authorization tokens or subject headers against `SpiceDBClient.check_permission()`.
2. Campaigns, sessions, and character sheets enforce permission boundaries governed by `libs/runefoble_auth/schema/runefoble.zed`.
3. Requests violating Zanzibar relationships return HTTP 403 Forbidden with structured permission diagnostic details.
4. Unit tests verify authorization rejection and pass-through for DM, Player, and Spectator subjects.
