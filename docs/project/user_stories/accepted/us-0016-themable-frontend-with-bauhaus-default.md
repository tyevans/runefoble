---
id: 0016
title: Themable Frontend Design System with Bauhaus Modernist Default
status: Accepted
created: 2026-09-25
persona: Devon (The Live Streamer / Modder)
feature: FEAT-UI-01
---

# US-0016 — Themable Frontend Design System with Bauhaus Modernist Default

## User Story

**As a** tabletop player, GM, or live streamer,
**I want** the Runefoble user interface to be fully themable using CSS custom property design tokens, with a bold Bauhaus modernist visual identity as the default,
**So that** the board, cards, controls, and chronicles feature clean geometric typography, primary color blocks (cadmium red, cobalt blue, warm yellow), crisp black structural borders, and offset hard drop-shadows, while allowing easy switching between themes (e.g. Bauhaus, Dark Fantasy, Parchment, Cyber Rune).

## Scenario 1: Default Bauhaus Visual Appearance
```gherkin
Given a user loads the Runefoble web application at "http://localhost/"
When the application mounts without prior local storage overrides
Then the active theme is "bauhaus"
And the document root attribute is data-theme="bauhaus"
And UI components (board, tokens, character cards, modals) render with:
  | Token | Value |
  | Primary Accent | Cadmium Red (#D62828 / #E63946) |
  | Secondary Accent | Cobalt Blue (#1D3557 / #00509D) |
  | Tertiary Accent | Canary Yellow (#F7B731 / #FCBF49) |
  | Canvas Background | Warm Modernist Paper (#F8F9FA / #F4F1DE) |
  | Borders | 2px solid #111111 |
  | Box Shadow | 4px 4px 0px #111111 |
```

## Scenario 2: Switching Themes Persistently
```gherkin
Given a user is viewing the Runefoble application in Bauhaus theme
When the user clicks the theme switcher and selects "Dark Fantasy"
Then data-theme="dark-fantasy" is applied to the root element
And the color palette transitions to deep obsidian, violet runes, and gold accents
And the selection is saved in local storage under "runefoble-theme"
And reloading the page restores the "Dark Fantasy" theme automatically.
```
