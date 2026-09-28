---
id: 0068
title: Application Shell View Audit, Deep Route Wiring, and Dev API Proxying
status: Accepted
created: 2026-09-27
persona: Alex (The Developer / Plugin Modder) & Devon (The Live Streamer / Spectator)
feature: FEAT-UI-13
governing_prd: PRD-0023
---

# US-0068 — Application Shell View Audit, Deep Route Wiring, and Dev API Proxying

## Governing PRD
- [`PRD-0023: Unified Frontend Experience with User Authentication, Campaign Hub, and Session Orchestration`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)

## User Story

**As a** Platform Engineer developing features locally or a Spectator following a direct deep link,
**I want** all standard routes in the App Shell to cleanly mount their intended view components, resolve dynamic titles for breadcrumbs from live backend APIs, and proxy REST and WebSocket traffic seamlessly through the local Vite development server,
**So that** developing, testing, and navigating the application works end-to-end without missing routes, stub fallbacks, 404 network errors, or broken child paths.

## Persona Motivations & Permissions
- **Alex (Platform Developer)**: Needs the local Vite dev server at `http://localhost:5173` to proxy `/api/v1` and `/ws` to `localhost:8000` so that local frontend development hits live Gateway API services instead of silently failing and hitting mock fallbacks. Needs every defined route to mount a distinct, validated component.
- **Devon (Spectator / Streamer)**: Enters the app via deep links (e.g. `#/campaigns/:id`, `#/profile`, `#/campaigns/:id/characters`) and expects proper breadcrumb labels (`Campaigns > Shadows of Drakkenheim > Party Roster`), clean navigation, and zero view-routing collisions.

## Scenario 1: Local Vite Development Server Proxies API & WebSocket Calls
```gherkin
Given a developer is running the frontend via "pnpm run dev" on "http://localhost:5173"
And the Gateway API is running on "http://localhost:8000"
When the frontend issues a fetch request to "/api/v1/campaigns"
Then the Vite dev server proxies the request to "http://localhost:8000/api/v1/campaigns"
And returns the live HTTP 200 response with real campaign records
And WebSocket connection attempts to "/ws/session/:id" are upgraded and proxied to the gateway backend.
```

## Scenario 2: Dynamic Route Title Resolution from API Records
```gherkin
Given the user navigates directly to "#/campaigns/camp-1790564858218"
When the router initializes and parses the route parameters
Then the router invokes the title resolver for entity "campaign" and ID "camp-1790564858218"
And fetches the title dynamically from the cached or live campaign record
And renders breadcrumb text "Home > Campaigns > Tomb of the Star-Eater" instead of "Campaign #camp-1790564858218".
```

## Scenario 3: Deep Route Wiring for Party Roster and Profile Views
```gherkin
Given an authenticated user is on the application
When the user navigates to "#/campaigns/camp-1790564858218/characters"
Then "getActiveView()" resolves view "campaign-characters" rather than colliding with "campaign-detail"
And mounts the campaign party character roster component
When the user navigates to "#/profile"
Then "getActiveView()" resolves view "profile" rather than defaulting to "campaigns"
And renders the user profile settings panel.
```
