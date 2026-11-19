---
id: '0890'
title: Zitadel Access Tokens Carry the Username Claim
status: Complete
created: 2026-11-19
dependencies:
- '0887'
governing_adrs:
- ADR-0005
- ADR-0015
governing_prds: []
governing_stories:
- US-0009
target_bc: core
target_release: 0.9.0
---

# TASK-0890: Zitadel Access Tokens Carry the Username Claim

## Status

Complete

## Summary

Zitadel JWT access tokens carry no `preferred_username`. The services verify the access token, so `VerifiedPrincipal.username` is `None` for every real sign-in, and member lists show user ids. Add a Zitadel Action in the bootstrap Job that sets `preferred_username` in the access token. Remove the TS verifier fallback that makes a username from `sub`.

## Problem Statement

- `deployments/zitadel_bootstrap/src/zitadel_bootstrap/provisioning.py`: sets `accessTokenType: JWT` and configures no Action.
- `libs/runefoble_auth/src/runefoble_auth/zitadel.py` reads `preferred_username` (no fallback after TASK-0887).
- `services/audience_studio/src/identity/zitadelVerifier.ts:131`: makes the username from `sub` when the claim is absent. ADR-0015 does not allow a made-up value.
- `e2e/steps/campaign_hub_steps.ts:127` expects the owner row to contain `Evelyn`. It fails on Kind.

## Documentation & Architecture Review

- `docs/reference/identity-and-token-contract.md`: list the claim and its source.
- Zitadel Actions v1 "Complement Token" flow, trigger "Pre access token creation": `api.v1.claims.setClaim('preferred_username', ctx.v1.getUser().username)` (confirm the exact API on the deployed Zitadel version with context7 or the Zitadel docs).

## Product & User Story References

- US-0009: the DM manages members by name.

## Detailed Specification & Implementation Plan

1. The bootstrap Job creates or updates the Action and binds it to the Complement Token flow, Pre access token creation trigger. Running the Job again changes nothing (idempotent, as the rest of `provision`).
2. audience_studio verifier: username is `null` when the claim is absent. Update its tests.
3. Update the identity contract doc and `docs/how-to/authenticate-with-zitadel-oidc.md`.

## Frontdoor Blackbox Test Plan

- Bootstrap unit tests against the existing fake management API pattern in the bootstrap package tests: the Action is created once, and a second run creates nothing.
- audience_studio test: a token without `preferred_username` yields a null username.
- Orchestrator on Kind: after `make helm-deploy`, `e2e/features/campaign_hub.feature` passes with real sign-in.

## Definition of Done

- Tests above pass. `campaign_hub.feature` passes on Kind. Docs and CHANGELOG `Fixed` entry.

## Audit Provenance

- Severity: medium
- Source audits: .audit/work/0887.md
