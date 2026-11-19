---
id: '0887'
title: Campaign Members Show Verified Names, Not Derived IDs
status: Complete
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0011
- ADR-0013
- ADR-0014
- ADR-0015
governing_prds: []
governing_stories:
- US-0009
target_bc: game_session
target_release: 0.9.0
---

# TASK-0887: Campaign Members Show Verified Names, Not Derived IDs

## Status

Complete

## Summary

The campaign member list makes each member name from the user id. Zitadel ids are numbers, so every member shows as an id such as `400279375238397981`. Record the verified username of the member when the member enters the campaign, and show it in the member list. A profile `display_name` that the member edited takes priority.

## Problem Statement

- `services/game_session/src/game_session/campaign/service_membership.py:38` `display_name(user_id)` strips prefixes like `dm-` from the id and title-cases it. This worked only for the dev ids that the e2e harness used before TASK-0525.
- `service_membership.py:138` sets `username=display_name(user_id)` for every member, including the owner.
- `libs/runefoble_events/src/runefoble_events/campaign_lifecycle.py`: `CampaignCreated` has `owner_id` only, and `CampaignMemberAdded` has `user_id` and `role` only. No event records a name.
- `services/game_session/src/game_session/profile/aggregate.py`: the profile stores only edited fields. The username default comes from the caller's token at read time, so it is not available for other users.
- Observed: `e2e/steps/campaign_hub_steps.ts:127` expects the owner row to contain `Evelyn`. It shows the Zitadel id.

## Documentation & Architecture Review

- ADR-0011: the name is recorded in the domain event that adds the member. The membership state holds it.
- ADR-0015: no invented values. If a token has no username, store none and show the id; do not make a name from the id.
- `docs/reference/identity-and-token-contract.md`: confirm which Zitadel claim supplies `VerifiedPrincipal.username` and update the doc if it is wrong.

## Product & User Story References

- US-0009 (campaign access control): the DM manages members by name.

## Detailed Specification & Implementation Plan

1. Add `owner_username: str | None` to `CampaignCreated` and `username: str | None` to `CampaignMemberAdded`. Set them from the verified principal of the caller who creates or joins. A role change by the owner must not overwrite the member's name with the owner's name.
2. Campaign and membership state keep the name per user. Delete `display_name(user_id)` and every call site.
3. The member list returns, per member: the edited profile `display_name` if one exists (same bounded context, profile aggregate), else the recorded username, else `null`. The UI already falls back to `user_id` on `null`.
4. No migration shim: events without the field read as `None` because the field is optional by schema, which is the honest value.
5. Update `docs/reference/events-catalog-platform.md` and the campaign members API reference.

## Frontdoor Blackbox Test Plan

- Create a campaign with a token whose `preferred_username` is `evelyn`. Join with a second token (`marcus`) through the invite route. `GET /api/v1/campaigns/{id}/members` returns `evelyn` for the owner and `marcus` for the player.
- Marcus edits his profile `display_name` to `Marcus the Bold`. The member list shows `Marcus the Bold`.
- The owner changes Marcus's role. Marcus's name stays `marcus`-based, not the owner's.
- A token with no username: the member entry has `username: null`. No name is made from the id.
- Playwright: `e2e/features/campaign_hub.feature` passes on Kind (`make test-e2e ARGS="--workers=1 --project=chromium e2e/features/campaign_hub.feature"`, run by the orchestrator).

## Definition of Done

- The tests above pass. `display_name(user_id)` is gone.
- Event catalogue and API reference updated. CHANGELOG `Fixed` entry.

## Audit Provenance

- Severity: medium
- Source audits: e2e campaign_hub run on Kind, 2026-11-19
