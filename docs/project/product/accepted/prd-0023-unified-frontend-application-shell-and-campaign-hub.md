---
id: '0023'
title: Unified Frontend Experience with User Authentication, Campaign Hub, and Session Orchestration
status: Accepted
created: 2026-09-27
---

# PRD-0023 — Unified Frontend Experience with User Authentication, Campaign Hub, and Session Orchestration

## Who this is for

Tabletop roleplaying Game Masters (like Evelyn), casual voice-first players (like Marcus), absent players (like Sarah), content creators (like Devon), and community developers (like Alex) who need a cohesive web application to sign up, manage campaigns, organize character rosters, assemble in pre-game lobbies, and launch live VTT sessions without being trapped in a static, hardcoded demo sandbox.

## What the person cannot do today

Currently, Runefoble provides rich backend domain microservices and isolated board mechanics, but the web frontend is restricted to a static demo page:
- **No User Onboarding or Authentication**: Users cannot register a new account, log in with Zitadel OIDC, view their profile, or maintain a persistent authenticated session.
- **No Campaign Management**: Game Masters cannot create new campaigns, view a list of campaigns, invite party members via shareable invite codes/links, or administer SpiceDB Zanzibar access control roles (Owner, DM, Player, Spectator).
- **No Character Roster or Party Assignment**: Players cannot browse their library of created characters, create new characters outside of raw API calls, or select which character joins an active campaign party.
- **No Pre-Game Session Lobby or Launch Orchestration**: Sessions cannot be scheduled, listed, or launched from the UI. There is no pre-game lobby where players gather, toggle readiness, confirm roles, and verify audio before the DM starts the active game session.
- **No Client-Side Routing or Navigation**: The frontend lacks an application router; URLs cannot be bookmarked or shared (e.g. `#/campaigns/4/sessions/14`), and navigating between management views and the active tabletop requires restarting or hardcoding state in the App Shell.

## What good looks like

1. **Seamless User Authentication & Identity Flow**:
   - Clean, accessible sign-up and sign-in modal/views integrating self-hosted Zitadel OIDC with PKCE token exchange and local developer fallback.
   - Top-level application chrome displaying user avatar, display name, and active roles, with a dropdown menu for profile settings, switching campaigns, and secure logout.
   - Automatic token persistence and silent token refresh, gracefully redirecting unauthenticated visitors to login.

2. **Campaign Management Hub & Zanzibar Role Administration**:
   - Campaign Dashboard view (`#/campaigns`) presenting active, past, and invited campaigns in Bauhaus cards with quick status indicators (active session banner, player count, DM name).
   - "Create Campaign" wizard collecting campaign title, setting description, ruleset system (e.g. SRD 5e), and optional cover artwork.
   - Member management drawer with one-click invite link/code generation and intuitive role selection (Owner, Dungeon Master, Player, Spectator) mapping directly to SpiceDB Zanzibar relationship tuples.

3. **Character Roster & Campaign Party Assignment**:
   - Personal Character Roster view (`#/characters`) displaying character vitals, class, level, conditions, and equipped gear across campaigns.
   - "New Character" builder modal enabling creation of character sheets with portrait selection, ability scores, class, and background.
   - One-click party assignment linking owned characters to specific campaigns with SpiceDB ownership verification.

4. **Pre-Game Session Lobby & Live Launchpad**:
   - Campaign Session List and Pre-Game Lobby (`#/campaigns/:id/lobby/:sessionId`) where players assemble before a session.
   - Real-time player presence indicators (online/offline/absent), selected character lock-in, and player readiness toggles ("Ready to Play").
   - DM "Launch Session" action triggering the `POST /api/v1/sessions/{id}/start` domain event and transitioning all connected clients from Lobby to the Active VTT view.

5. **Client-Side SPA Routing & Responsive App Shell Navigation**:
   - Lightweight, dependency-free client router supporting deep-linkable URLs:
     - `#/login` & `#/register`
     - `#/campaigns` (Campaign Hub)
     - `#/campaigns/:id` (Campaign Detail & Member Roster)
     - `#/campaigns/:id/characters` (Campaign Party Roster)
     - `#/campaigns/:id/lobby/:sessionId` (Pre-Game Lobby)
     - `#/campaigns/:id/sessions/:sessionId` (Active Tabletop Session)
     - `#/profile` (User Settings)
   - Navigation bar with dynamic breadcrumbs (`Home > Campaign #4 > Session 14`), network connectivity badge, mode switcher (Party vs. Spectator), and global settings modal trigger.
   - Route-aware WebSocket lifecycle management: WebSockets only open upon entering an active session or lobby route and cleanly teardown when navigating away.

## What this does not do

- It does not replace the microfrontend architecture established in ADR-0013; bounded context components remain vendored in `services/<bc>/ui/` and aggregated in Storybook.
- It does not bypass Zanzibar authorization; all campaign creation, character editing, and session launching actions are strictly validated against SpiceDB relations.
- It does not require heavyweight full-stack frameworks (like Next.js or Nuxt); routing and state orchestration remain lightweight Lit Web Components with minimal bundle footprint.

## What it costs at scale

- Client-side route transitions and token refresh timers require careful memory hygiene and event listener disposal to prevent memory leaks during multi-hour tabletop sessions.
- Campaign dashboards with high campaign counts require paginated REST API responses to maintain sub-100ms render speeds.

## Checkable Outcomes

1. Unauthenticated users visiting protected routes are smoothly routed to the login view, and logging in stores a valid JWT and transitions to `#/campaigns` in <100ms.
2. A Game Master can create a campaign, generate an invite link, and assign player roles in under 30 seconds via the Campaign Hub.
3. A player can select a character from their personal roster, join a campaign party, and toggle "Ready" in the Pre-Game Session Lobby.
4. When the DM clicks "Launch Session", all connected lobby participants transition simultaneously to the active VTT board within 500ms over WebSockets.
5. All new components render with high-contrast Bauhaus design tokens, pass WCAG 2.1 AA accessibility invariants in dark and light modes, and have interactive Storybook stories with zero console errors.

## Linked User Stories

- [`US-0062: User Registration, Zitadel OIDC Authentication, and Profile Management`](../../user_stories/accepted/us-0062-user-registration-zitadel-auth-and-profile.md)
- [`US-0063: Campaign Creation, Dashboard Hub, and SpiceDB Zanzibar Member Access Control`](../../user_stories/accepted/us-0063-campaign-creation-dashboard-and-zanzibar-roles.md)
- [`US-0064: Character Roster Management and Campaign Party Assignment`](../../user_stories/accepted/us-0064-character-roster-management-and-party-assignment.md)
- [`US-0065: Game Session Pre-Game Lobby, Participant Readiness, and Live Launch Orchestration`](../../user_stories/accepted/us-0065-game-session-lobby-readiness-and-launch.md)
- [`US-0066: Application Shell Client-Side Routing, Navigation Chrome, and Route Lifecycle`](../../user_stories/accepted/us-0066-client-side-routing-navigation-and-breadcrumbs.md)
- [`US-0067: Campaign Detail View, Setting Management, and Session Scheduling`](../../user_stories/accepted/us-0067-campaign-detail-view-and-session-scheduling.md)
- [`US-0068: Application Shell View Audit, Deep Route Wiring, and Dev API Proxying`](../../user_stories/accepted/us-0068-app-shell-view-audit-and-api-proxying.md)
- [`US-0069: Interactive Character Sheet Inspector and Active Session VTT Binding`](../../user_stories/accepted/us-0069-character-sheet-inspector-and-active-session-binding.md)
- [`US-0070: User Account Settings and Profile Management View`](../../user_stories/accepted/us-0070-user-account-settings-and-profile-management.md)
- [`US-0071: Campaign Dashboard Creation Idempotency and Lifecycle Management`](../../user_stories/accepted/us-0071-campaign-dashboard-idempotency-and-lifecycle.md)

## Implementing Backlog Tasks

- [`TASK-0206: Frontend SPA Client Router and Navigation Chrome`](../../backlog/complete/0206-frontend-spa-client-router-and-navigation-chrome.md)
- [`TASK-0207: Zitadel Auth Client and Login Modal Component`](../../backlog/complete/0207-zitadel-auth-client-and-login-modal-component.md)
- [`TASK-0208: Gateway Campaign Lifecycle and Membership API`](../../backlog/complete/0208-gateway-campaign-lifecycle-and-membership-api.md)
- [`TASK-0209: Campaign Dashboard and Creation Microfrontend`](../../backlog/complete/0209-campaign-dashboard-and-creation-microfrontend.md)
- [`TASK-0210: Campaign Members and Zanzibar Role Manager UI`](../../backlog/complete/0210-campaign-members-and-zanzibar-role-manager-ui.md)
- [`TASK-0211: Character Roster and Party Assignment Microfrontend`](../../backlog/complete/0211-character-roster-and-party-assignment-microfrontend.md)
- [`TASK-0212: Game Session Lobby and Readiness Microfrontend`](../../backlog/complete/0212-game-session-lobby-and-readiness-microfrontend.md)
- [`TASK-0213: App Shell View Orchestration and Session Transition`](../../backlog/complete/0213-app-shell-view-orchestration-and-session-transition.md)
- [`TASK-0214: Frontend Routing and Auth Blackbox Test Suite`](../../backlog/complete/0214-frontend-routing-and-auth-blackbox-test-suite.md)
- [`TASK-0215: Campaign Management and Lobby Blackbox Test Suite`](../../backlog/complete/0215-campaign-management-and-lobby-blackbox-test-suite.md)
- [`TASK-0246: Gateway Campaign Sessions API and Persistence`](../../backlog/refined/0246-gateway-campaign-sessions-api-and-persistence.md)
- [`TASK-0247: Frontend Vite API Proxy and Dynamic Route Title Resolver`](../../backlog/refined/0247-frontend-vite-api-proxy-and-dynamic-route-title-resolver.md)
- [`TASK-0248: Campaign Detail Hero Header and Metadata Component`](../../backlog/refined/0248-campaign-detail-hero-header-and-metadata-component.md)
- [`TASK-0249: Session Scheduling and Staging Lobby Creation Modal`](../../backlog/proposed/0249-session-scheduling-and-staging-lobby-creation-modal.md)
- [`TASK-0250: Unified Campaign Detail View Orchestration and Tabbed Navigation`](../../backlog/proposed/0250-unified-campaign-detail-view-orchestration-and-tabbed-navigation.md)
- [`TASK-0251: App Shell Views Enumeration, Wiring Audit, and Blackbox Test Suite`](../../backlog/proposed/0251-app-shell-views-enumeration-and-wiring-audit-test-suite.md)
- [`TASK-0252: Gateway Character Management Router and Zanzibar Authorization`](../../backlog/refined/0252-gateway-character-management-router-and-zanzibar-auth.md)
- [`TASK-0253: Character Aggregate Campaign Assignment and Core Attributes Extension`](../../backlog/refined/0253-character-aggregate-campaign-assignment-and-stats.md)
- [`TASK-0254: Frontend Character Roster Event Binding and Data Mutations`](../../backlog/proposed/0254-frontend-character-roster-event-binding-and-mutations.md)
- [`TASK-0255: Character Sheet Route and Inspector Subview Orchestration`](../../backlog/proposed/0255-character-sheet-route-and-inspector-subview.md)
- [`TASK-0256: Dynamic Character Binding in Pre-Game Lobby and Active VTT`](../../backlog/proposed/0256-dynamic-character-binding-in-lobby-and-active-vtt.md)
- [`TASK-0257: Profile Settings View and Campaign Creation Idempotency`](../../backlog/proposed/0257-profile-settings-view-and-campaign-creation-dedup.md)
- [`TASK-0258: Character Management and Tabletop Sync Blackbox Test Suite`](../../backlog/proposed/0258-character-management-and-vtt-sync-blackbox-test-suite.md)
