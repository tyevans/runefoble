---
icon: lucide/palette
---

# Storybook UI Component Studio

Runefoble uses a component-driven frontend architecture built with **Lit Web Components**, **Bauhaus design tokens**, and **Storybook**. Every service microfrontend (`the_watcher`, `board_state`, `character_sheet`, `game_session`, `voice_agent`) builds and validates its UI elements in Storybook isolation before composition into the lightweight App Shell.

<div style="margin: 1.5rem 0; display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;">
  <a href="storybook/" target="_blank" class="md-button md-button--primary">
    🚀 Launch Fullscreen Storybook
  </a>
  <a href="how-to/develop-lit-components-in-storybook/" class="md-button">
    📖 Storybook Development Guide
  </a>
  <a href="reference/design-tokens-and-themes/" class="md-button">
    🎨 Design Tokens & Themes
  </a>
</div>

<div style="position: relative; width: 100%; height: 85vh; min-height: 600px; border-radius: 8px; overflow: hidden; border: 1px solid rgba(127, 127, 127, 0.25); box-shadow: 0 4px 20px rgba(0,0,0,0.15);">
  <iframe src="storybook/" style="width: 100%; height: 100%; border: none;" allowfullscreen title="Runefoble Storybook UI Studio"></iframe>
</div>

---

## Explored Components & Microfrontends

- **🎲 Tactical Board (`<runefoble-board>`)**: Kinetic tokens, grid snapping, 5-foot measurement rulers, hazard zones, and spoken movement ghost previews.
- **👁️ The Watcher AI Feed (`<runefoble-watcher-feed>`)**: Narrative event streaming, intent proposals, atmospheric recaps, and DM veto controls.
- **📜 Character Cards (`<runefoble-character-card>`)**: Live HP meters, condition tags, drunk/foolishness absence penalties, and inventory trackers.
- **🎙️ Voice Agent & Audio Indicator (`<runefoble-voice-controls>`)**: WebRTC audio streaming, live frequency spectrum visualizer, and DM voice modulator.
- **⚙️ Settings & Theme Matrix (`<runefoble-settings-modal>`)**: Bauhaus light and dark mode switches, WCAG contrast compliance, and color palettes.
