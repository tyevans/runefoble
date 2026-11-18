# How-To: Interact with Character Sheet Inventory, Equipment & Condition Tracker

This guide explains how to use the interactive digital character sheet microfrontend (`<runefoble-character-sheet>`) to equip gear, manage inventory encumbrance, inspect active conditions and absence penalties, and track spell slots.

## Authentication and Permissions

Every route needs a bearer token. Set `TOKEN` to a Zitadel access token for the caller. Without a valid token the route returns 401. The service verifies the token itself. It ignores `X-User-Id` and similar headers.

Each route checks one SpiceDB permission on the character in the path. The schema in `libs/runefoble_auth/schema/runefoble.zed` decides who passes:

| Routes | Permission | Who passes |
|---|---|---|
| `GET /api/v1/characters/{id}`, and the `GET` guardrails, portrait, and wardrobe routes | `view` | Owner, campaign DM, and campaign members |
| All `POST`, `PUT`, `PATCH`, and `DELETE` routes on a character (health, penalties, inventory, equipment, conditions, spells, level-up, stand-in, guardrails, campaign, wardrobe, portrait) | `edit` | Owner and campaign DM. A player who is not the owner gets 403. |
| `POST /api/v1/crafting/recipes/combine` (character in the body) | `edit` | Owner and campaign DM |
| `DELETE /api/v1/characters/{id}` on the gateway | `delete` | Owner only. The DM gets 403. |

Response codes:
- 401: no valid bearer token.
- 403: the caller lacks the permission. The body names the permission.
- 400: the request is valid, but the domain rejects it. For example, a penalty or condition is not active. Nothing is saved.
- 422: the body is malformed.
- 503: SpiceDB cannot answer, or it does not apply an ownership write. The service does not allow the request, and it does not report success.
- 503: the event store is unreachable. The write is not saved, no event is published, and the character does not change. Retry when the store is back.

Character creation writes the owner tuple before it stores the character. If the write fails, the response is 503 and no character exists.

---

## 1. Visual Paper Doll & Click-to-Equip Interaction

The character sheet provides dedicated interactive paper doll slots for core equipment:
- **`main_hand`**: Weapons, wands, or tools.
- **`off_hand`**: Shields, focuses, or secondary weapons.
- **`armor`**: Light, medium, heavy armor, or mystical robes.
- **`accessory`**: Rings, amulets, or cloaks.

### Equipping & Unequipping
1. **Equip**: Click the **"Equip"** button next to any item in the inventory list. The item is placed in its designated slot and dispatches the `equip-item` CustomEvent (`{ slot, itemName, itemId }`).
2. **Unequip**: Click the red **"✕"** button on any filled paper doll slot. The item returns to general carried inventory and dispatches the `unequip-item` CustomEvent (`{ slot, itemName }`).

---

## 2. Dynamic Encumbrance Capacity Bar

The encumbrance bar dynamically sums the total weight of all carried items (`quantity * weight_lbs`) and compares it against character Strength thresholds:

| Load Tier | Capacity Threshold | Visual Indicator | Movement & Tactical Penalty |
|---|---|---|---|
| **Light** | $\le 33\%$ capacity | Blue (`var(--rf-accent-secondary)`) | None |
| **Medium** | $\le 66\%$ capacity | Teal / Green (`#2a9d8f`) | Normal movement |
| **Heavy** | $\le 100\%$ capacity | Yellow (`var(--rf-accent-tertiary)`) | Speed reduced by 10 ft |
| **Overburdened** | $> 100\%$ capacity | Red (`var(--rf-accent-primary)`) | Speed reduced by 20 ft; disadvantage on Str/Dex checks |

---

## 3. Condition Indicators & Absence Badges

The sheet displays both rules-as-written 5e/d20 tactical conditions and Runefoble absence penalties:
- **Tactical Conditions** (`blinded`, `prone`, `stunned`, `poisoned`, etc.): Rendered with blue geometric badges and tactical icons (`⚡`, `👁️`, `🔻`).
- **Runefoble Absence Penalties** (`drunk`, `foolishness`, `greed`, `cowardice`): Inflicted when human players miss a session and their character is piloted by The Watcher AI stand-in. Rendered with yellow warning badges (`🍺`, `🤡`, `💰`).

### Interactive Tooltips
Hover over or click any condition badge to reveal an informational popover showing:
- Exact mechanical consequences (e.g. "Attack rolls against creature have advantage").
- Saving throw modifiers (e.g. "Disadvantage on Dex saves vs physical pushes").
- Source attribution (e.g. Tactical condition vs DM Absence Penalty).

---

## 4. Spellbook & Spell Slot Tracker

Spellcasters can manage their magical reserves without manual pen-and-paper tracking:
1. **Clickable Pips**: Each spell tier (1 to 9) displays available slots as solid circles (`●`) and expended slots as empty rings (`○`).
   - Click an available slot (`●`) to expend it (dispatches `expend-slot`).
   - Click an expended slot (`○`) to restore it during short/long rests (dispatches `restore-slot`).
2. **Prepared Spells**: Click **"Cast"** next to any prepared spell to expend an appropriate slot tier.
3. **Spellbook Management**: Click **"Prepare"** or **"Unprepare"** in the known spellbook to swap daily prepared spells.

---

## 5. Microfrontend Embedding

```html
<runefoble-character-sheet
  characterId="c-valeros-12"
  apiBaseUrl="/api/v1/characters"
  characterName="Valeros the Bold"
  characterClass="Fighter 4 / Wizard 1"
  .level="${5}"
  .currentHp="${38}"
  .maxHp="${44}"
  .armorClass="${18}"
  .strength="${16}"
  .equipment="${{ main_hand: 'Longsword +1', off_hand: 'Steel Shield', armor: 'Chain Mail' }}"
  @equip-item="${(e) => handleEquip(e.detail)}"
  @unequip-item="${(e) => handleUnequip(e.detail)}"
  @cast-spell="${(e) => handleCast(e.detail)}"
></runefoble-character-sheet>
```

---

## 6. Character Roster & Campaign Party Assignment

The Character Roster microfrontend (`<runefoble-character-roster>`) and builder modal (`<runefoble-character-builder-modal>`) allow players to maintain a persistent library of adventurers across campaigns.

### Character Roster View (`<runefoble-character-roster>`)
The roster displays a responsive grid of owned adventurers with:
- **Portrait & Identity**: Avatar thumbnail, character name, class/subclass, and level badge.
- **Vitals Display**: Dynamic health bar (with warning state for low HP $\le 30\%$), Armor Class shield, and movement speed.
- **Campaign Assignment Badge**: Indicates whether the character is actively attached to a campaign party (`🏰 Tomb of the Star-Eater`) or available as an unassigned free agent (`○ Unassigned`).
- **Search & Filter Controls**: Text filtering across name, class, subclass, and campaign, plus quick status filter pills (**All**, **Assigned**, **Unassigned**).

### Quick Actions & CustomEvents
| Button | Event Dispatched | Detail Payload | Description |
|---|---|---|---|
| **"Inspect Sheet"** | `@inspect-character` | `{ characterId, character }` | Navigates to full character sheet view or opens character details. |
| **"Assign to Campaign"** | `@assign-campaign` | `{ characterId, campaignId, campaignTitle }` | Opens party assignment dialog to link character to an active campaign or unassign. |
| **"Delete"** | `@delete-character` | `{ characterId }` | Opens confirmation dialog. No API route serves deletion yet: the gateway has no delete route and `character_sheet` has no delete operation (TASK-0585). |
| **"+ Create Character"** | `@create-character` | `CreateCharacterPayload` | Opens builder modal and emits character creation payload upon submission. |

### Character Builder Modal (`<runefoble-character-builder-modal>`)
Provides a validated form for creating new adventurers:
1. **Identity**: Character Name (required), Class (SRD 5e standard classes), and optional Subclass.
2. **Combat Vitals**: Level (1–20), Max HP ($> 0$), Armor Class, and Movement Speed (5-ft increments).
3. **Ability Scores**: STR, DEX, CON, INT, WIS, CHA scores with real-time automatic modifier calculations ($\lfloor(\text{score} - 10) / 2\rfloor$).
4. **Token Portrait**: Predefined geometric portrait presets or custom avatar URLs.

### Example Embedding
```html
<runefoble-character-roster
  .characters="${playerCharacters}"
  .campaigns="${activeCampaigns}"
  current-user-id="usr-marcus"
  @create-character="${(e) => saveCharacter(e.detail)}"
  @assign-campaign="${(e) => updatePartyAssignment(e.detail)}"
  @inspect-character="${(e) => openSheet(e.detail.characterId)}"
  @delete-character="${(e) => deleteCharacter(e.detail.characterId)}"
></runefoble-character-roster>
```

---

## 7. Backend Aggregate & Campaign Assignment REST API

The event-sourced `CharacterAggregate` and `CharacterState` persist core 5e character attributes and campaign party assignment:

### Core Character Attributes
- **`subclass`** (`Optional[str]`): Specialization path (e.g. `"Evocation"`, `"Champion"`).
- **`armor_class`** (`int`, default `10`): Defensive rating.
- **`speed_ft`** (`int`, default `30`): Base movement speed per tactical turn.
- **`ability_scores`** (`dict[str, int]`): Standard 5e scores (`str`, `dex`, `con`, `int`, `wis`, `cha`, default `10` each).
- **`campaign_id`** (`Optional[str]`): UUID or slug of assigned campaign.

### Campaign Assignment Endpoint
To attach or detach an adventurer to an active campaign party, issue a `PATCH` request:

```http
PATCH /api/v1/characters/{character_id}/campaign
Content-Type: application/json
Authorization: Bearer {TOKEN}

{
  "campaign_id": "camp-9812-frontier"
}
```

The service records the verified caller from the bearer token as `assigned_by`. The request body does not set it.

To unassign an adventurer back to free agent status in the player roster:
```json
{
  "campaign_id": null
}
```

### Domain Event & Zanzibar Security
1. **Domain Event**: `runefoble.events.character.assigned_to_campaign` (`runefoble.events.character.assigned_to_campaign`) is created and applied to the event stream, then published to the `runefoble.events.character` Redis stream.
2. **SpiceDB Synchronization**: Writing or removing the Zanzibar relationship `character:{id}#campaign@campaign:{campaign_id}` enforces fine-grained authorization under `runefoble.zed`.

---

## 8. App Shell Inspector Subview & Deep Route Orchestration

The application shell (`frontend/src/runefoble-app.ts`) routes `#/characters/:characterId` directly into the dedicated `'character-sheet'` inspector subview (`TASK-0255`).

### Subview Capabilities
1. **Direct Deep-Linking**: Users navigating to `#/characters/:characterId` or clicking **"Inspect Sheet"** from the character roster immediately mount `<runefoble-character-sheet>` populated with character vitals, equipment, carried inventory, and spell slots loaded via `appDataService.fetchCharacter(characterId)`.
2. **Stand-In Guardrails Policies**: Accompanied by `<runefoble-stand-in-guardrails>` to inspect and configure spell slot preservation, protected party allies, and tactical posture for when The Watcher pilots the adventurer during player absence.
3. **Dynamic Breadcrumbs**: Automatically resolves entity names into hierarchical breadcrumbs (`Home > Characters > [Character Name]`).
4. **Header Navigation**: Features a prominent **"← Back to Roster"** button returning players to `#/characters`.

---

## 9. Sub-Resource Mutations & Event-Sourced Persistence (TASK-0356)

Per ADR-0002, ADR-0004, ADR-0007, and ADR-0013, sub-resource mutations on `<runefoble-character-sheet>` are wired to backend persistence via Gateway API endpoints and App Shell event bindings:

### Gateway API Sub-Resource Endpoints
All sub-resource mutations enforce the SpiceDB Zanzibar `edit` permission on the target character. The `GET` guardrails route enforces `view`. If the Character Sheet service is unreachable, the gateway returns 503:
- **`POST /api/v1/characters/{id}/health`**: Mutates HP by `delta`, clamps between $[0, \text{maxHp}]$, and triggers stand-in permadeath safeguard stabilization (`is_stabilized = True`, `unconscious_stabilized` condition) when HP $\le 0$.
- **`POST /api/v1/characters/{id}/equipment`**: Equips item to slot (`main_hand`, `off_hand`, `armor`, `accessory`).
- **`DELETE /api/v1/characters/{id}/equipment/{slot}`**: Unequips item from slot, returning it to inventory.
- **`POST /api/v1/characters/{id}/inventory`**: Adds item to inventory with item ID, quantity, and weight.
- **`DELETE /api/v1/characters/{id}/inventory/{item_id}`**: Removes item (or decrements quantity) from inventory.
- **`POST /api/v1/characters/{id}/conditions`**: Applies condition with tactical source.
- **`DELETE /api/v1/characters/{id}/conditions/{condition}`**: Removes condition and associated penalties.
- **`POST /api/v1/characters/{id}/spells/cast`**: Consumes an available spell slot of the specified level.
- **`POST /api/v1/characters/{id}/spells/prepare`**: Toggles spell preparation status.

### Interactive UI Enhancements
1. **Interactive HP Delta Buttons**: `stats.template.ts` features quick adjustment buttons (`-5`, `-1`, `+1`, `+5`) that invoke `sheet.handleHpDelta(delta)` with instant visual feedback and optimistic state clamping.
2. **Equip Slot Selector Modal**: `inventory.template.ts` presents an interactive slot selection dialog when clicking "Equip", allowing players to select target equipment slot (`main_hand`, `off_hand`, `armor`, `accessory`).
3. **Spell Level Casting**: `spells.template.ts` passes the spell's actual known tier (`spell.level`) to `handleCastSpell` rather than hardcoding tier 1.

### App Shell Action Event Handlers
`frontend/src/runefoble-app.ts` binds all 11 action events emitted by `<runefoble-character-sheet>`:
- `@hp-change`, `@equip-item`, `@unequip-item`, `@add-item`, `@remove-item`, `@cast-spell`, `@prepare-spell`, `@apply-condition`, `@remove-condition`, `@expend-slot`, `@restore-slot`.
Event handlers execute optimistic local cache updates, invoke `appDataService` persistence methods, and display informative toast notifications.
