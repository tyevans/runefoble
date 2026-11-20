---
id: '0973'
title: The Invite Link Field Shows Only the Newest Link
status: Refined
created: 2026-11-19
dependencies:
- '0950'
governing_adrs:
- ADR-0013
- ADR-0014
- ADR-0023
governing_prds:
- PRD-0025
governing_stories:
- us-0063-campaign-creation-dashboard-and-zanzibar-roles
target_bc: game_session
target_release: 1.0.0
---

# TASK-0973: The Invite Link Field Shows Only the Newest Link

## Status

Refined

## Summary

On Kind (2026-11-19), the step "Evelyn generates a player invite link in the UI and copies it" read token A from the link field, but the clipboard held token B. The field still showed an earlier invite (`app.inviteUrl` persists), the step accepted it, and Generate then replaced it. A DM can also copy a stale link that way.

## Detailed Specification & Implementation Plan

1. When the DM presses Generate Link, the App Shell clears `inviteUrl` until the reply arrives; the field and Copy Link are empty and disabled while the request is out. A failed request shows the error and no link.
2. Opening the invite modal for another campaign shows no link from the previous campaign.
3. The e2e step `generatePlayerLink` (`e2e/steps/campaign_invite_join_steps.ts:43-51`) waits for a link that differs from the value before the click.

## Frontdoor Blackbox Test Plan

- DOM test of `<runefoble-campaign-members>` and the shell action: after Generate, the field is empty until the reply; the copy writes the new link only.
- Orchestrator on Kind: `campaign_invite_join.feature` passes twice in a row.
