---
id: 0009
title: Fine-Grained Zanzibar Access Control for Campaign Roles
status: Accepted
created: 2026-09-25
persona: Evelyn (The Overworked Dungeon Master)
feature: FEAT-SEC-01
---

# US-0009 — Fine-Grained Zanzibar Access Control for Campaign Roles

## User Story

**As a** Dungeon Master managing a campaign,
**I want** object-scoped authorization enforced via SpiceDB Zanzibar rules,
**So that** players can only manipulate their assigned characters, spectators can only observe, and I retain full control over secret notes and monster tokens without security leaks.

## Scenario: Preventing Unauthorized Token Dragging
```gherkin
Given player Bob owns character "Valeros" (token "t1") but does not own character "Kyra" (token "t2")
When Bob attempts to send a move command for token "t2"
Then SpiceDB evaluates `board_token:t2#move@user:bob`
And the check returns `false`
And the API Gateway rejects the request with HTTP 403 Forbidden.
```
