# Microfrontends in Tabletop Roleplaying Domains

Tabletop roleplaying platforms (TTRPGs) like Runefoble unite deeply divergent domain concerns into a single real-time interface:
- Tactical spatial positioning and geometric line-of-sight (Board State).
- Character attributes, spell slots, inventory, and session absence penalties (Character Sheet).
- Turn order, dice physics, and clean streaming overlays (Game Session).
- Voice streaming, transcription, and speech-to-intent parsing (Voice Agent).
- Autonomous AI dungeon mastering, chronicle feeds, and NPC decisions (The Watcher).

## Why Centralized Frontends Break Down

When all user interface code is concentrated in a monolithic application directory, several failure modes emerge:

1. **Broken Domain Ownership**: A team modifying the character absence penalty logic in `services/character_sheet/` must navigate to a disconnected `frontend/src/components/` directory to adjust penalty badge presentation.
2. **Coupled Release Cycles**: A bug in the dice roller component can block deployment of an unrelated tactical board bugfix.
3. **Bloated Host Shells**: The top-level application container inevitably becomes an accumulator for state management, styling, and business rules belonging to other domains.

## The Web Components Solution

Runefoble adopts W3C Custom Elements and Lit as its microfrontend substrate rather than heavier iframe-based or multi-framework setups:

1. **Zero Framework Bloat**: Lit elements compile down to standard browser primitives. Loading five microfrontends does not require bundling five different framework runtimes.
2. **True Style Encapsulation with CSS Variable Penetration**: The Shadow DOM prevents CSS collision between complex widgets (e.g. board grid shaders versus character card layouts), while allowing global Bauhaus theme tokens (`var(--rf-*)`) to cascade naturally across shadow roots.
3. **Decoupled DOM Communication**: Components communicate up to the App Shell via standard DOM CustomEvents (`@move-token`, `@voice-toggle`), keeping presentation components completely decoupled from backend network transports.
4. **Flexible Embedding**: Because each microfrontend is a custom element, components like `<runefoble-spectator-view>` or `<runefoble-board>` can be embedded outside the main application—for instance in OBS streaming overlays or headless tournament views—without changes to the component source.

## The App Shell Pattern

In Runefoble's architecture, the App Shell (`frontend/src/runefoble-app.ts`) is strictly a conductor, not a performer. It manages:
- Layout and viewport grid responsiveness.
- Session WebSocket connection and network event distribution.
- Application-wide theming controls and mode selection.
- Assembly and composition of the domain microfrontends.

This division ensures that domain services remain autonomous vertical slices while users experience a unified, seamless game table.
