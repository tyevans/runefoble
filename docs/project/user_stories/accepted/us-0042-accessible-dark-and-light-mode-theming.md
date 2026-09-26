---
id: '0042'
title: Accessible Dark and Light Mode Theming Invariants Across Components
status: Accepted
created: 2026-09-25
persona: Marcus (The Tactician / Adventurer)
feature: FEAT-UI-03
governing_prd: PRD-0013
---

# US-0042 — Accessible Dark and Light Mode Theming Invariants Across Components

## Governing PRD
- [`PRD-0013: Immersive & Intuitive Frontend Experience with Tactile Board Kinematics`](../../product/accepted/prd-0013-immersive-and-intuitive-frontend-experience.md)

## User Story

**As an** adventurer playing long nighttime sessions on a laptop or mobile tablet,  
**I want** every board component, character card, and feed element to render with proper semantic contrast and readable typography in both dark and light modes,  
**So that** my eyes don't suffer fatigue, text remains legible per WCAG 2.1 AA standards, and tactile drop-shadows and borders remain distinct across all themes.

## Scenario 1: Contrast Invariant in Dark Mode
```gherkin
Given the application is running in "data-color-mode='dark'"
When viewing the tactical board, character card, watcher feed, and dice roller
Then all surface backgrounds consume semantic tokens (--rf-bg-surface, --rf-bg-card)
And primary text maintains at least a 7:1 contrast ratio against the background
And drop-shadows and borders remain visually distinct without blending into pitch black.
```

## Scenario 2: Bauhaus Theme in Dark Mode
```gherkin
Given the active theme is "bauhaus"
When the user switches appearance mode to "dark"
Then the canvas changes to charcoal/black (--rf-bg-canvas: #121212)
And structural borders render in high-contrast off-white (--rf-border-color: #f8f9fa)
And iconic primary color blocks (cadmium red, cobalt blue, canary yellow) adjust for dark contrast.
```
