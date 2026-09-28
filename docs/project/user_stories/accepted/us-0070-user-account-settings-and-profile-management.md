---
id: 0070
title: User Account Settings and Profile Management View
status: Accepted
created: 2026-09-27
persona: Marcus (The Voice-First Casual Adventurer) & Evelyn (The Overworked Dungeon Master)
feature: FEAT-UI-07
governing_prd: PRD-0023
---

# US-0070 — User Account Settings and Profile Management View

## Governing PRD
- [`PRD-0023: Unified Frontend Experience with User Authentication, Campaign Hub, and Session Orchestration`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)

## User Story

**As an** authenticated player, Game Master, or streamer,
**I want** to click "Account Settings" in the navigation user menu to navigate to `#/profile` and view my profile details (Zitadel user ID, username, email, assigned platform roles, and theme preferences),
**So that** I can verify my identity, review my permissions, and configure my account without being stranded on the default campaign dashboard.

## Persona Motivations & Permissions
- **Marcus (Player / Casual Adventurer)**: Clicks "Account Settings" from the avatar menu to verify his logged-in identity, view his active campaign memberships, and configure his audio/voice preferences.
- **Evelyn (Game Master)**: Needs to verify her assigned global roles (`dm`, `admin`) to confirm she has permissions to create and manage campaigns in SpiceDB Zanzibar.
- **Devon (Live Streamer / Spectator)**: Wants to verify stream privacy settings, toggle spectator presentation mode, and configure dark/light appearance tokens.
- **Alex (Developer / Modder)**: Uses the profile endpoint `GET /api/v1/profile` to inspect Zitadel OIDC claims, token expiration, and verify authorization headers.

## Scenario 1: Navigating to Account Settings from User Menu
```gherkin
Given Marcus is logged in and viewing any page in the application
When Marcus opens the user avatar dropdown menu and clicks "Account Settings"
Then the application router navigates to "#/profile"
And the App Shell renders the User Profile Settings view
And does not fall through to the default Campaign Dashboard.
```

## Scenario 2: Inspecting Profile Identity and Roles
```gherkin
Given Marcus is on "#/profile" with an active session
When the profile view mounts
Then it queries "GET /api/v1/profile" through the Gateway API
And displays Marcus's username ("valeros"), email ("marcus@example.com"), and User ID ("user-valeros")
And renders role badges for his active permissions ("player", "dm")
And displays his current theme and appearance mode selection.
```

## Scenario 3: Unauthenticated Access Guard
```gherkin
Given an unauthenticated visitor directly navigates to "http://localhost/#/profile"
When the route guard evaluates the path
Then the visitor is redirected to "#/login" with a return redirect parameter
And the User Profile Settings view is protected from unauthenticated access.
```
