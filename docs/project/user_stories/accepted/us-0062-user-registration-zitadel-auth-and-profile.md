---
id: 0062
title: User Registration, Zitadel OIDC Authentication, and Profile Management
status: Accepted
created: 2026-09-27
persona: Marcus (The Voice-First Casual Adventurer)
feature: FEAT-UI-07
governing_prd: PRD-0023
---

# US-0062 — User Registration, Zitadel OIDC Authentication, and Profile Management

## Governing PRD
- [`PRD-0023: Unified Frontend Experience with User Authentication, Campaign Hub, and Session Orchestration`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)

## User Story

**As a** tabletop player or Game Master,
**I want** to register an account, securely sign in via Zitadel OIDC, manage my user profile, and maintain a persistent authenticated session in the web browser,
**So that** my campaign memberships, character ownerships, and session permissions are recognized across all devices without having to use hardcoded developer mock accounts.

## Scenario 1: User Sign-Up and Sign-In via Auth Modal
```gherkin
Given an unauthenticated visitor navigates to "http://localhost/#/login"
When the visitor opens the sign-in modal and provides valid credentials
Then the authentication client exchanges credentials with Zitadel for a secure JWT
And the user session is stored in localStorage
And the application redirects to the Campaign Dashboard at "#/campaigns"
And the top navigation chrome displays the user avatar and username.
```

## Scenario 2: Token Expiration and Graceful Logout
```gherkin
Given an authenticated user with an expired JWT token
When the user attempts to perform an authenticated action
Then the auth client attempts a background refresh
And if refresh fails, the user is cleanly logged out
And localStorage session tokens are cleared
And the application redirects to "#/login" with a session expiration notice.
```
