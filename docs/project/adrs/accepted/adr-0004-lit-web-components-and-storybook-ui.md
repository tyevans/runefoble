# ADR-0004: Frontend Component Architecture with Lit, Vite, and Storybook

## Context

Runefoble requires a reactive, visually rich frontend that renders:
- Tactical map grids with animated token movements.
- Character status cards with live HP bars and condition badges.
- Real-time voice and narrative chronicle feeds.
- Low memory footprint and framework-agnostic interoperability.

## Decision

We build the frontend using **Lit (Web Components)**, **Vite**, and **Storybook**:

1. **Lit Web Components**: Standard W3C custom elements encapsulated with shadow DOM, ensuring zero CSS bleeding and native browser performance.
2. **Storybook for Component-Driven Development**: Every UI element (board, card, feed, dice roller) is first built and tested in Storybook isolation before composition into the main view.
3. **Vite Bundler**: Fast ESM-based development server and production bundler.
4. **TypeScript Strictness**: Type safety across all component properties, events, and API payloads.

## Consequences

- Components can be reused across desktop, mobile web, or embedded overlays (e.g. streaming overlays).
- Storybook serves as a living design system and visual test suite.
- Clean separation between presentation logic and backend services.
