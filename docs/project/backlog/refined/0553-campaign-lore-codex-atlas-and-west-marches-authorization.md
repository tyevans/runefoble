---
id: '0553'
title: Campaign Lore Codex, Search, Atlas, Handout, Relic, and West Marches Authorization
status: Refined
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0540
- TASK-0541
- TASK-0542
- TASK-0531
- TASK-0536
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0007
- PRD-0015
- PRD-0018
governing_stories:
- US-0036
- US-0050
- US-0045
- US-0058
target_release: 0.9.0
severity: critical
source_audits:
- w2-campaign-lore.md
- w3-authz-coverage.md
---

# TASK-0553: Campaign Lore Codex, Search, Atlas, Handout, Relic, and West Marches Authorization

## Status
Refined

## Summary
Campaign lore has the most authorization defects of any service in the platform. A codex entry is readable and editable through another campaign's path. The search route trusts a body field that names the caller, so a player reads DM-only secrets. Atlas layer and territory writes have no check. Handout, relic, and West Marches writes pass for anonymous callers and for spectators. Codex publish is open to anonymous callers and accepts any privacy string. This task fixes each of these, binds each route to a schema permission, and makes the gateway forward the caller identity.

## Problem Statement
- Cross-campaign codex access: `services/campaign_lore/src/campaign_lore/codex_deps.py:57-80` (`load_codex_entry`) never compares the entry's campaign to the path campaign. Probe: a player of campaign A reads a campaign B entry through A's path (200) (`w2-campaign-lore.md` F1).
- Search: `services/campaign_lore/src/campaign_lore/routers/search.py:69` (`user_id = req.caller_id or header_user_id`). Probe: a player with a spoofed body `caller_id` gets secret chunks (`w2-campaign-lore.md` F2).
- Atlas: `routers/atlas.py:232-258` (`toggle_layer`) and `:260-297` (`update_territory`) have no check. Probe: anonymous calls return 200 and 201 (`w2-campaign-lore.md` F3). `routers/atlas.py:135-175` (`create_pin`) uses `view`, so spectators place pins. `atlas.place_pin` is the schema permission (`w2-campaign-lore.md` F5).
- Handouts, relics, West Marches: `permissions.py:34-101` returns `True` when `user_id` is falsy (lines 41, 58, 75, 92, 101). Handout generate, relic forge, West Marches link, discovery, stronghold upgrade, and notices pass for anonymous callers and spectators (`w2-campaign-lore.md` F4).
- Codex publish (`routers/codex/entries.py:31`): `author_id` falls back to `anonymous_author`. The check is view-only. `privacy` is `str` (`routers/codex/schemas.py`), so any value is accepted (`w2-campaign-lore.md` F13).
- Codex shared privacy: `codex_deps.py:83-93` writes `party_shared` and `public` relations that TASK-0540 adds to the schema (`w2-campaign-lore.md` F8).
- Gateway hub views (`gateway/api/src/gateway_api/routers/hub_views.py:16-25`): the proxy sends no identity header, so every gateway call is anonymous (`w2-campaign-lore.md` F14). The fallback data is removed in the fake-implementation task.
- Documents and aliases: `routers/documents.py:53` (ingest) takes identity from a raw header with no check. `routers/aliases.py:49` (consolidate) has no check (`w3-authz-coverage.md` rows 123, 130).
- Relic translate-rune (`routers/relics.py:191`) has no check (`w3-authz-coverage.md` row 136).
- Tests: `tests/test_blackbox_campaign_atlas_and_codex.py` and `tests/test_blackbox_campaign_lore_rag.py` write permission names as tuples (`w2-campaign-lore.md` F21). They are migrated here.

## Documentation & Architecture Review
- ADR-0001 mapping for this context: `codex_entry.view`, `codex_entry.edit`, `codex_entry.manage` (author or run_session). `lore_document.read_secret` and `lore_document.manage`. `atlas.edit` and `atlas.place_pin`. `diegetic_handout.interact`. `relic.inspect`. `shared_world.discover` and `shared_world.manage`. `stronghold.upgrade`.
- ADR-0007: lore state belongs to the lore context. The gateway forwards identity and routes; it does not hold lore state (`w2-campaign-lore.md` F14, fixed here for identity only).
- ADR-0014: test setup uses public routes (campaign creation, invite, role route, document ingest, codex publish).
- `docs/how-to/index-campaign-lore-with-redstring.md`, `docs/how-to/interact-with-campaign-atlas-and-codex.md`, `docs/how-to/forge-print-ready-maps-standees-and-stl-tokens.md`, and `docs/how-to/coordinate-west-marches-shared-world-and-caravans.md` describe these routes. Update the auth text.
- `docs/reference/events-schema.md` is not changed here.

## Product & User Story References
- US-0036 (RAG-indexed lore). US-0050 (atlas and living codex). US-0045 (handouts and relic inspector). US-0058 (West Marches). PRD-0007, PRD-0015, PRD-0018.

## Detailed Specification & Implementation Plan
1. `permissions.py`: every `check_user_can_*` returns False for a missing principal. The principal comes from TASK-0531.
2. Codex:
   - `load_codex_entry` loads the entry and compares `state.campaign_id` to the path campaign. A mismatch returns 404 (not 403) so that entry existence is not revealed.
   - Publish: require the principal and `campaign.play`. Set `author` to the principal. Validate `privacy` as an enum `private`, `party_shared`, `public`. Write the `codex_entry` tuples per the privacy value. A write error returns 503 and the entry is not saved.
   - Read and edit use `codex_entry.view` and `codex_entry.edit`. Remove the campaign-level grant shortcut that bypasses the entry's own relations.
3. Search (`search.py`): TASK-0531 removes `caller_id`. This task adds the per-document secret check. The caller is the principal from TASK-0531.
4. Atlas: layer toggle and territory update require `atlas.edit`. Pin creation requires `atlas.place_pin`. Territory updates update the existing territory when one exists (the duplicate-row defect `w2-campaign-lore.md` F12 is out of scope; record the dependency in the index).
5. Handouts: generate requires `campaign.run_session`. Break seal and invisible-ink reveal require `diegetic_handout.interact`.
6. Relics: forge requires `campaign.run_session`. Inspect and translate-rune require `relic.inspect`.
7. West Marches: link world requires `campaign.manage`. Discovery requires `shared_world.discover`. Stronghold upgrade requires `stronghold.upgrade`. Tavern notice requires `shared_world.discover`.
8. Documents and aliases: ingest and consolidate require `lore_document.manage`.
9. Gateway `hub_views.py`: forwarding is TASK-0536. Do not repeat it here.
10. Delete the local `get_spicedb_client` and import the library factory.
11. Migrate the two test files named above. Setup writes go through public routes.

## Frontdoor Blackbox Test Plan
Setup: two campaigns, a DM and a player in each, a spectator in campaign A, codex entries and documents created through public routes.
- Before the fix, the player of A reads a privacy-`party_shared` entry of B through A's path: 200. After the fix it returns 404.
- Search with a player body `caller_id` set to the DM returns no secret chunk. The DM search returns the secret chunk.
- Anonymous `POST /api/v1/campaigns/A/atlas/layers/toggle` returns 401. A spectator gets 403. A player gets 200.
- A spectator `POST .../atlas/pins` returns 403.
- Anonymous `POST /api/v1/lore/relics/forge` returns 401. Before the fix it returns 200.
- Anonymous codex publish returns 401. `privacy: "whatever"` returns 422.
- `party_shared` publish by a DM, then a player of the same campaign reads it: 200. A spectator reads it: 403.

## Definition of Done
1. Frontdoor tests exist in `tests/test_blackbox_lore_authz.py` and pass against the live harness. Both migrated test files pass.
2. No `return True` on a no-identity path remains in `services/campaign_lore/src/campaign_lore/permissions.py` or `codex_deps.py`.
3. `caller_id` is absent from the search request schema.
4. Codex privacy values are validated and the `party_shared` and `public` tuples are written and checked.
5. The lore how-to docs in the Documentation section are updated.
6. `uv run pytest services/campaign_lore gateway/api` passes for the changed tests. `uv run ruff check` passes.
7. No file in the change exceeds 500 lines. `routers/codex/entries.py` and `routers/atlas.py` are split if needed.
