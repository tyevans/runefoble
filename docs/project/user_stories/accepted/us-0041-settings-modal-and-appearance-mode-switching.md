---
id: '0041'
title: Settings Modal with Dark/Light/System Mode & Integrated Theme Switcher
status: Accepted
created: 2026-09-25
persona: Devon (The Live Streamer / Modder)
feature: FEAT-UI-02
---

# US-0041 — Settings Modal with Dark/Light/System Mode & Integrated Theme Switcher

## User Story

**As a** tabletop streamer or player,  
**I want** a dedicated settings dialog accessible via a clean header button where I can toggle between Dark, Light, and System appearance modes and choose my preferred visual theme,  
**So that** the top navigation remains decluttered while allowing me to easily adjust interface appearance for streaming environments, night play, or system OS changes.

## Scenario 1: Opening Settings Dialog and Changing Color Mode
```gherkin
Given a user is running the Runefoble web application
When the user clicks the "Settings" gear button in the application header
Then the "<runefoble-settings-modal>" dialog opens with focus trapped inside
And the user can view options for "System Default", "Light Mode", and "Dark Mode"
When the user selects "Dark Mode"
Then "data-color-mode='dark'" is applied to the root document
And the choice is saved to local storage under "runefoble-color-mode"
And closing the modal returns focus to the settings button.
```

## Scenario 2: Switching Themes inside the Settings Modal
```gherkin
Given a user has opened the settings modal
When the user clicks the "Cyber Rune" theme card
Then "data-theme='cyber-rune'" is applied to the root document
And the selection is saved in local storage under "runefoble-theme"
And all active Web Components update their design token variables immediately.
```
