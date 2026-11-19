# Gateway Route Ownership

This table names the owning service for each Watcher route that the gateway exposes. The
gateway only forwards these routes. It holds no Watcher state and runs no Watcher logic.

Status values:

- `proxy`: the gateway forwards the route to the owner. A browser calls the gateway path.
- `internal`: the owner serves the route, but the gateway does not expose it. The gateway
  does not proxy an owner alias.

Rules that the table follows:

- A browser reaches only `/api` on the gateway. So the gateway proxies the `/api/v1` form of a
  route. A bare owner path (for example `/factions/...`) is internal.
- When an owner route has two `/api/v1` forms, the gateway proxies the canonical form only.
- Each proxy row is a `ProxyRoute` in `gateway/api/src/gateway_api/routers/watcher_proxy_*.py`.
  Speak-and-act is in `watcher_speech_proxy.py` (TASK-0583).

## The Watcher

| Gateway path | Method | Owner path | Status | Module |
|---|---|---|---|---|
| `/api/v1/watcher/speak-and-act` | POST | `/api/v1/watcher/intent` | proxy (TASK-0583) | `watcher_speech_proxy.py` |
| `/api/v1/watcher/transcribe-and-act` | POST | `/api/v1/watcher/transcribe-and-act` | proxy | `watcher_proxy_intent.py` |
| `/api/v1/watcher/intent/parse` | POST | `/api/v1/watcher/intent/parse` | proxy | `watcher_proxy_intent.py` |
| `/api/v1/watcher/intent/resolve` | POST | `/api/v1/watcher/intent/resolve` | proxy | `watcher_proxy_intent.py` |
| `/api/v1/watcher/intent/execute` | POST | `/api/v1/watcher/intent/execute` | proxy | `watcher_proxy_intent.py` |
| `/api/v1/watcher/scenes/generate` | POST | `/api/v1/watcher/scenes/generate` | proxy (LLM timeout) | `watcher_proxy_dm.py` |
| `/api/v1/watcher/encounters/spawn` | POST | `/api/v1/watcher/encounters/spawn` | proxy | `watcher_proxy_dm.py` |
| `/api/v1/watcher/encounters/npc-turn` | POST | `/api/v1/watcher/encounters/npc-turn` | proxy | `watcher_proxy_dm.py` |
| `/api/v1/watcher/narrate` | POST | `/api/v1/watcher/narrate` | proxy (LLM timeout) | `watcher_proxy_dm.py` |
| `/api/v1/watcher/stand-in/act` | POST | `/api/v1/watcher/stand-in/act` | proxy (LLM timeout) | `watcher_proxy_dm.py` |
| `/api/v1/watcher/stand-in/recap` | POST | `/api/v1/watcher/stand-in/recap` | proxy | `watcher_proxy_dm.py` |
| `/api/v1/watcher/chronicle/recap` | POST | `/api/v1/watcher/chronicle/recap` | proxy | `watcher_proxy_dm.py` |
| `/api/v1/watcher/whispers` | GET | `/api/v1/watcher/whispers` | proxy | `watcher_proxy_dm.py` |
| `/api/v1/watcher/whispers` | POST | `/api/v1/watcher/whispers` | proxy | `watcher_proxy_dm.py` |
| `/api/v1/watcher/whispers/generate` | POST | `/api/v1/watcher/whispers/generate` | proxy (LLM timeout) | `watcher_proxy_dm.py` |
| `/api/v1/watcher/actions/propose` | POST | `/api/v1/watcher/actions/propose` | proxy | `watcher_proxy_dm.py` |
| `/api/v1/watcher/actions/propose` (alias) | POST | `/api/v1/watcher/propose` | internal (owner alias) | none |
| `/api/v1/watcher/actions/pending` | GET | `/api/v1/watcher/actions/pending` | proxy | `watcher_proxy_dm.py` |
| `/api/v1/watcher/veto` | POST | `/api/v1/watcher/veto` | proxy | `watcher_proxy_dm.py` |
| `/api/v1/watcher/approve` | POST | `/api/v1/watcher/approve` | proxy | `watcher_proxy_dm.py` |
| `/api/v1/watcher/modify` | POST | `/api/v1/watcher/modify` | proxy | `watcher_proxy_dm.py` |
| `/api/v1/campaigns/{campaign_id}/world-tick` | POST | `/api/v1/campaigns/{campaign_id}/world-tick` | proxy | `watcher_proxy_factions.py` |
| `/api/v1/campaigns/{campaign_id}/world-tick` (alias) | POST | `/api/v1/campaigns/{campaign_id}/factions/tick` | internal (owner alias) | none |
| `/api/v1/campaigns/{campaign_id}/factions` | POST | `/api/v1/campaigns/{campaign_id}/factions` | proxy | `watcher_proxy_factions.py` |
| `/api/v1/campaigns/{campaign_id}/factions` | GET | `/api/v1/campaigns/{campaign_id}/factions` | proxy | `watcher_proxy_factions.py` |
| `/api/v1/campaigns/{campaign_id}/factions/{faction_id}` | GET | `/api/v1/campaigns/{campaign_id}/factions/{faction_id}` | proxy | `watcher_proxy_factions.py` |
| `/api/v1/campaigns/{campaign_id}/world-ticks/latest` | GET | `/api/v1/campaigns/{campaign_id}/world-ticks/latest` | proxy | `watcher_proxy_factions.py` |
| `/api/v1/factions/{faction_id}/resources/adjust` | POST | `/api/v1/factions/{faction_id}/resources/adjust` | proxy | `watcher_proxy_factions.py` |
| `/api/v1/factions/{faction_id}/resources/adjust` (alias) | POST | `/factions/{faction_id}/resources/adjust` | internal (owner alias) | none |
| `/api/v1/factions/{faction_id}/bribery/resolve` | POST | `/api/v1/factions/{faction_id}/bribery/resolve` | proxy | `watcher_proxy_factions.py` |
| `/api/v1/factions/{faction_id}/bribery/resolve` (alias) | POST | `/factions/{faction_id}/bribery/resolve` | internal (owner alias) | none |
| `/api/v1/factions/{faction_id}/mercenaries/recruit` | POST | `/api/v1/factions/{faction_id}/mercenaries/recruit` | proxy | `watcher_proxy_factions.py` |
| `/api/v1/factions/{faction_id}/mercenaries/recruit` (alias) | POST | `/factions/{faction_id}/mercenaries/recruit` | internal (owner alias) | none |
| `/api/v1/factions/{faction_id}/resources` | GET | `/api/v1/factions/{faction_id}/resources` | proxy | `watcher_proxy_factions.py` |
| `/api/v1/factions/{faction_id}/resources` (alias) | GET | `/factions/{faction_id}/resources` | internal (owner alias) | none |
| `/api/v1/factions/skirmish/simulate` | POST | `/api/v1/factions/skirmish/simulate` | proxy | `watcher_proxy_factions.py` |
| `/api/v1/factions/skirmish/simulate` (alias) | POST | `/the-watcher/factions/skirmish/simulate` | internal (owner alias) | none |
| `/api/v1/regions/{region_id}/unrest` | GET | `/api/v1/regions/{region_id}/unrest` | proxy | `watcher_proxy_factions.py` |
| `/api/v1/regions/{region_id}/unrest` (alias) | GET | `/the-watcher/regions/{region_id}/unrest` | internal (owner alias) | none |
| `/ui/manifest` | GET | `/ui/manifest` | internal (owner microfrontend manifest) | none |

## Owner rules

- The owner checks every object permission (ADR-0001). The gateway adds no role check.
- The gateway passes the caller's bearer token to the owner. The owner verifies it again (ADR-0015 c).
- The gateway does not read `user_id`, `approver_id`, or `dm_id` from a body. The owner uses the verified caller.
- Routes marked "LLM timeout" wait `RUNEFOBLE_WATCHER_LLM_PROXY_TIMEOUT_S` (default 15 s). The owner's inference worker call waits up to 10 s.
- Veto and approve are forwarded unchanged. The DM decision applies in the owner (ADR-0002).
