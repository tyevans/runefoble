---
id: 0012
title: Campaign Telemetry, Analytics & Historical Memory Archive
status: Accepted
created: 2026-09-25
---

# PRD-0012 — Campaign Telemetry, Analytics & Historical Memory Archive

## Who this is for

Absent players (Sarah) catching up on party history, content creators (Devon) displaying stream infographics, and DMs (Evelyn) reviewing encounter balance and pacing telemetry.

## What the person cannot do today

Multi-session campaigns produce vast quantities of events and stories, but players have no unified way to review historical milestones, battle statistics, combat heatmaps, or party achievements over time.

## What good looks like

- **Living Campaign Timeline**: An interactive, navigable visual timeline tracking past sessions, epic boss battles, character deaths, and acquired relics.
- **Combat Telemetry & Spatial Heatmaps**: Post-session analytics revealing lethal map coordinates, party damage distribution, healing output, and MVP turn awards.
- **Player Achievement & Milestone Badges**: Automatically derived milestones (e.g. "Survived 100 Goblins", "Most Critical Fumbles", "Unbroken Attendance").

## What this does not do

- It does not collect invasive user privacy data; all telemetry is strictly game-mechanic domain event aggregates.
- It does not overwrite the narrative chronicle; it provides analytical companions to The Watcher's narrative text.

## What it costs at scale

Asynchronous projection workers consuming Redis Streams events and populating partitioned analytics tables in PostgreSQL.

## Checkable Outcomes

1. Post-session analytics dashboard displays combat telemetry, MVP metrics, and damage heatmaps.
2. Interactive campaign timeline renders past session milestones and chronicle highlights.
3. Absent players can query past session stats alongside their audio recap.

## Linked User Stories
- [`US-0040: Campaign Combat Telemetry and Living Interactive Timeline`](../../user_stories/accepted/us-0040-campaign-combat-telemetry-and-living-timeline.md)
- [`US-0054: Post-Session Combat Spatial Heatmaps and Party Damage Analytics`](../../user_stories/accepted/us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md)

## Implementing Backlog Tasks
- [`TASK-0038: OpenPanel Privacy-Preserving Analytics SDK & Event Pipeline`](../../backlog/complete/0038-openpanel-analytics-service-and-event-pipeline.md)
- [`TASK-0052: Campaign Analytics & Chronicle Archive Microservice`](../../backlog/proposed/0052-campaign-analytics-and-chronicle-archive-bc.md)
- [`TASK-0082: OpenPanel Analytics SDK & Worker Modular Decomposition`](../../backlog/complete/0082-analytics-sdk-and-worker-modular-decomposition.md)
- [`TASK-0097: OpenPanel Analytics Blackbox Test Suite Modular Decomposition`](../../backlog/proposed/0097-openpanel-analytics-blackbox-test-suite-decomposition.md)
- [`TASK-0110: Campaign Telemetry Dashboard and Chronicle Timeline Microfrontend`](../../backlog/proposed/0110-campaign-telemetry-dashboard-and-chronicle-timeline-microfrontend.md)
