# How to Manage Campaign Lifecycle and Membership Invites

This recipe demonstrates how to create campaigns, generate shareable invite tokens, join existing campaigns, and inspect active party membership. The `game_session` service owns these records and their SpiceDB Zanzibar tuples (ADR-0015 decision a). It is the only service that writes them.

Clients call these routes through the Gateway API. The gateway checks the bearer token and forwards each call to `game_session`. It keeps no campaign state (see section 10).

## Prerequisites

- Local Kind cluster or developer environment running (`make cluster-up` or `uv run pytest`).
- A Zitadel JWT bearer token for each caller. There is no developer header mode. Identity comes only from a verified token (ADR-0015 c).
- SpiceDB running locally on port `50051`.

---

## 1. Creating a New Campaign

When creating a new campaign via `POST /api/v1/campaigns`, the API automatically:
1. Generates a unique campaign identifier (UUID).
2. Persists campaign metadata (title, description, setting, system, and settings) in the event store.
3. Writes the `campaign:<id>#owner@user:<user_id>` relationship tuple to SpiceDB Zanzibar. The tuple is written only after the save succeeds.

It also seeds a `Session #1: Staging Lobby` unless the request sets `"seed_initial_session": false`.

```bash
curl -X POST "http://localhost:8000/api/v1/campaigns" \
  -H "Authorization: Bearer <ZITADEL_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Shadows of Drakkenheim",
    "description": "Gothic horror urban survival campaign.",
    "setting": "Gothic Fantasy",
    "system": "5e",
    "settings": {
      "ruleset": "2024",
      "gritty_realism": true
    }
  }'
```

**Response (`201 Created`):**
```json
{
  "id": "6f1c2b8e-3a4d-4e5f-9a7b-8c9d0e1f2a3b",
  "title": "Shadows of Drakkenheim",
  "description": "Gothic horror urban survival campaign.",
  "setting": "Gothic Fantasy",
  "system": "5e",
  "status": "active",
  "owner_id": "dm-evelyn",
  "role": "owner",
  "member_count": 1,
  "settings": {
    "ruleset": "2024",
    "gritty_realism": true
  },
  "created_at": "2026-09-27T10:15:00Z",
  "updated_at": "2026-09-27T10:15:00Z"
}
```

---

## 2. Listing Viewable Campaigns

`GET /api/v1/campaigns` lists only campaigns where the requesting user has the Zanzibar `view` permission (granted to owners, DMs, players, and spectators).

```bash
curl -X GET "http://localhost:8000/api/v1/campaigns" \
  -H "Authorization: Bearer <ZITADEL_JWT>"
```

**Response (`200 OK`):**
```json
[
  {
    "id": "6f1c2b8e-3a4d-4e5f-9a7b-8c9d0e1f2a3b",
    "title": "Shadows of Drakkenheim",
    "setting": "Gothic Fantasy",
    "system": "5e",
    "status": "active",
    "role": "owner",
    "permissions": {
      "view": true,
      "manage": true,
      "invite": true,
      "launch_session": true,
      "assign_roles": true
    },
    "member_count": 1
  }
]
```

Each campaign object carries a `permissions` object. `GET /api/v1/campaigns/{id}` returns the same object for one campaign. `game_session` computes every flag with a SpiceDB `check` for the caller. Each flag names the permission that the matching route checks:

| Flag | SpiceDB permission | Route that the flag gates |
|---|---|---|
| `view` | `view` | Read campaign, members, sessions |
| `manage` | `manage` | Update campaign, remove member, and the Campaign Hub owner controls |
| `invite` | `run_session` | `POST /api/v1/campaigns/{id}/invites` |
| `launch_session` | `run_session` | `POST /api/v1/campaigns/{id}/sessions`, lobby launch, and DM-only tools |
| `assign_roles` | `manage` | `POST /api/v1/campaigns/{id}/roles` |

The App Shell reads these flags and never compares role names. A flag only hides a control. The server checks every mutating route again, so a stale flag cannot grant access.

---

## 3. Generating Shareable Invite Links

Dungeon Masters and owners (holding `run_session` permission) can generate cryptographically secure shareable invite tokens. The token is shown once. The service stores only a hash of it.

- `expires_in_hours` defaults to 72. It must be at least 1. Send `null` for an invite that never expires.
- `max_uses` defaults to unlimited. It must be at least 1.

```bash
curl -X POST "http://localhost:8000/api/v1/campaigns/6f1c2b8e-3a4d-4e5f-9a7b-8c9d0e1f2a3b/invites" \
  -H "Authorization: Bearer <ZITADEL_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "player",
    "expires_in_hours": 72,
    "max_uses": 5
  }'
```

**Response (`201 Created`):**
```json
{
  "token": "dGVzdF9pbnZpdGVfdG9rZW4",
  "campaign_id": "6f1c2b8e-3a4d-4e5f-9a7b-8c9d0e1f2a3b",
  "role": "player",
  "invite_url": "/#/join/dGVzdF9pbnZpdGVfdG9rZW4",
  "expires_at": "2026-09-30T10:15:00Z",
  "created_at": "2026-09-27T10:15:00Z",
  "max_uses": 5,
  "uses": 0
}
```

---

## 4. Joining a Campaign via Invite

A player or spectator redeems an invite code via `POST /api/v1/campaigns/join`. The service writes the corresponding Zanzibar relation (`player` or `spectator`) after it saves the membership:

```bash
curl -X POST "http://localhost:8000/api/v1/campaigns/join" \
  -H "Authorization: Bearer <PLAYER_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "invite_token": "dGVzdF9pbnZpdGVfdG9rZW4"
  }'
```

| Case | Status | `detail.error` |
|---|---|---|
| Unknown token | `400` | `invalid_invite` |
| Invite past `expires_at` | `410` | `invite_expired` |
| `max_uses` reached | `409` | `invite_exhausted` |

A user who is already a member gets `200` again. The join does not use up another invite slot. The owner gets `200` with role `owner`.

**Response (`200 OK`):**
```json
{
  "status": "joined",
  "campaign_id": "6f1c2b8e-3a4d-4e5f-9a7b-8c9d0e1f2a3b",
  "user_id": "player-marcus",
  "role": "player",
  "zanzibar_relation": "campaign:6f1c2b8e-3a4d-4e5f-9a7b-8c9d0e1f2a3b#player@user:player-marcus"
}
```

---

## 5. Querying Campaign Members and Active Roles

Inspect the owner and every member via `GET /api/v1/campaigns/{id}/members`. The roster comes from the membership record that `game_session` owns. `username` is derived from the user ID. The gateway adds `character_name` from the characters assigned to the campaign, and it is `null` when none is assigned:

```bash
curl -X GET "http://localhost:8000/api/v1/campaigns/6f1c2b8e-3a4d-4e5f-9a7b-8c9d0e1f2a3b/members" \
  -H "Authorization: Bearer <PLAYER_JWT>"
```

**Response (`200 OK`):**
```json
[
  {
    "user_id": "dm-evelyn",
    "role": "owner",
    "subject_type": "user",
    "zanzibar_relation": "campaign:6f1c2b8e-3a4d-4e5f-9a7b-8c9d0e1f2a3b#owner@user:dm-evelyn",
    "username": "Evelyn",
    "character_name": null
  },
  {
    "user_id": "player-marcus",
    "role": "player",
    "subject_type": "user",
    "zanzibar_relation": "campaign:6f1c2b8e-3a4d-4e5f-9a7b-8c9d0e1f2a3b#player@user:player-marcus",
    "username": "Marcus",
    "character_name": "Marcus Aurelius the Paladin"
  }
]
```

### Assigning a Role to a Member

Assign a role with `POST /api/v1/campaigns/{id}/roles`. `game_session` owns this route. The caller must hold the `manage` permission on the campaign. Only the campaign owner holds `manage` by default. The grant is saved as a membership, so it appears in the roster. Then the SpiceDB relation is written.

- Grantable roles: `dungeon_master`, `game_master`, `player`, `spectator`.
- `owner` is not grantable. Ownership moves only with campaign creation. The route returns `422` for `owner`.
- A caller without `manage` gets `403` (`permission_denied`). A refused request writes no tuple.
- If the authorization store cannot write the relation, the owner answers `503`. The gateway returns `502`, because the owner's answer is an upstream 5xx. Retry the request: a repeated grant writes the relation again.
- To read the caller's SpiceDB flags (`manage`, `run_session`, `play`, `view`), call `GET /api/v1/campaigns/{id}/capabilities`. Non-members receive all flags as `false`. The `permissions` object on the campaign routes uses the App Shell names (see section 2).

```bash
curl -X POST "http://localhost:8000/api/v1/campaigns/6f1c2b8e-3a4d-4e5f-9a7b-8c9d0e1f2a3b/roles" \
  -H "Authorization: Bearer <OWNER_JWT>" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "dm-arthur", "role": "dungeon_master"}'
```

---

## 6. Removing a Member from a Campaign

Campaign owners and managers (holding `manage` permission) can remove members from a campaign via `DELETE /api/v1/campaigns/{campaign_id}/members/{user_id}`. The service saves the removal first. Then it revokes the user's `player`, `spectator`, `dungeon_master`, and `game_master` tuples on the campaign.

- The owner cannot be removed. The route returns `409` with `owner_not_removable`.
- The route is idempotent. Removing a user who is not a member returns `200`, and any leftover tuples are revoked.


```bash
curl -X DELETE "http://localhost:8000/api/v1/campaigns/6f1c2b8e-3a4d-4e5f-9a7b-8c9d0e1f2a3b/members/player-marcus" \
  -H "Authorization: Bearer <DM_JWT>"
```

**Response (`200 OK`):**
```json
{
  "status": "member_removed",
  "campaign_id": "6f1c2b8e-3a4d-4e5f-9a7b-8c9d0e1f2a3b",
  "user_id": "player-marcus"
}
```

---


## 7. Creating and Listing Campaign Sessions

Campaign owners and Dungeon Masters (holding `run_session` permission) can create staging lobbies and scheduled sessions using `POST /api/v1/campaigns/{campaign_id}/sessions`. All members (holding `view` permission) can list active and scheduled sessions via `GET /api/v1/campaigns/{campaign_id}/sessions`:

### Creating a Session / Staging Lobby
```bash
curl -X POST "http://localhost:8000/api/v1/campaigns/6f1c2b8e-3a4d-4e5f-9a7b-8c9d0e1f2a3b/sessions" \
  -H "Authorization: Bearer <DM_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Session #1: Crypt of the Sunken King",
    "status": "lobby",
    "description": "Pre-game character staging and readiness check."
  }'
```

**Response (`201 Created`):**
```json
{
  "id": "session-e7a9b1c2d4f54a6b8c9d0e1f2a3b4c5d",
  "campaign_id": "6f1c2b8e-3a4d-4e5f-9a7b-8c9d0e1f2a3b",
  "title": "Session #1: Crypt of the Sunken King",
  "status": "lobby",
  "round": 1,
  "participants_count": 0,
  "scheduled_at": null,
  "created_at": "2026-09-27T10:30:00Z"
}
```

### Listing Campaign Sessions
```bash
curl -X GET "http://localhost:8000/api/v1/campaigns/6f1c2b8e-3a4d-4e5f-9a7b-8c9d0e1f2a3b/sessions" \
  -H "Authorization: Bearer <PLAYER_JWT>"
```

**Response (`200 OK`):**
```json
[
  {
    "id": "session-e7a9b1c2d4f54a6b8c9d0e1f2a3b4c5d",
    "campaign_id": "6f1c2b8e-3a4d-4e5f-9a7b-8c9d0e1f2a3b",
    "title": "Session #1: Crypt of the Sunken King",
    "status": "lobby",
    "round": 1,
    "participants_count": 0,
    "scheduled_at": null,
    "created_at": "2026-09-27T10:30:00Z"
  }
]
```

---

## 8. Rendering Campaigns in the Web Component Microfrontend

The campaign hub UI is vendored by `@runefoble/game-session-ui/campaigns` using Lit Web Components:

```typescript
import '@runefoble/game-session-ui/campaigns';

// In your application template:
html`
  <runefoble-campaign-dashboard
    .campaigns=${campaignList}
    @select-campaign=${(e: CustomEvent) => {
      window.location.hash = `#/campaigns/${e.detail.campaignId}`;
    }}
    @create-campaign=${async (e: CustomEvent) => {
      const response = await fetch('/api/v1/campaigns', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(e.detail),
      });
      const newCampaign = await response.json();
      campaignList = [...campaignList, newCampaign];
    }}
  ></runefoble-campaign-dashboard>
`;
```

The `<runefoble-campaign-dashboard>` provides:
- Responsive Bauhaus card grids with elevation drop-shadows and role badges.
- Filtering by role ("All", "DMing", "Playing") and real-time text search.
- Active live session indicator (`● Session Live`).
- Seamless integration with the `<runefoble-campaign-creator>` dialog wizard.
- Modular styles decomposed under `@runefoble/game-session-ui/campaigns/styles/dashboard` (`base.styles.ts`, `cards.styles.ts`, `modal.styles.ts`) strictly < 130 lines per module.

---

## 9. Managing Campaign Members & Assigning Zanzibar Roles in the UI

The `<runefoble-campaign-members>` component allows Game Masters to inspect the party roster, assign SpiceDB Zanzibar roles (`dungeon_master`, `game_master`, `player`, `spectator`; the caller must hold `manage`), remove members safely via confirmation dialogs, and generate copyable invite links:

```typescript
import '@runefoble/game-session-ui/campaigns';

// In campaign view or settings modal:
html`
  <runefoble-campaign-members
    campaign-id="6f1c2b8e-3a4d-4e5f-9a7b-8c9d0e1f2a3b"
    campaign-title="Shadows of Drakkenheim"
    current-user-id="dm-evelyn"
    .canManage=${true}
    .members=${campaignMembers}
    invite-token="dGVzdF9pbnZpdGVfdG9rZW4"
    @assign-role=${async (e: CustomEvent) => {
      const { userId, role } = e.detail;
      await fetch(`/api/v1/campaigns/${campaignId}/roles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
        body: JSON.stringify({ user_id: userId, role }),
      });
    }}
    @remove-member=${async (e: CustomEvent) => {
      const { userId } = e.detail;
      // Revoke relations / remove membership
    }}
    @create-invite=${async (e: CustomEvent) => {
      const { role } = e.detail;
      const res = await fetch(`/api/v1/campaigns/${campaignId}/invites`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role }),
      });
      const data = await res.json();
    }}
  ></runefoble-campaign-members>
`;
```

Key features of `<runefoble-campaign-members>`:
- **Roster & Avatars**: Displays party member avatars, usernames, user IDs, and assigned characters.
- **SpiceDB Zanzibar Role Dropdown**: Enables owners (`canManage=true`) to change active relations between `dungeon_master`, `game_master`, `player`, and `spectator`. Only `manage` holders see it.
- **Protected Owner**: The campaign owner is protected with an immutable "Owner" badge.
- **Safe Removal with Confirmation**: Provides a confirmation modal before revoking campaign membership and Zanzibar permissions.
- **Interactive Invite Generator**: Modal generator with role pre-assignment, shareable link preview, and one-click clipboard copying.
- **View-Only Mode**: Regular players (`canManage=false`) see clean read-only role badges without destructive controls.
- **Modular Styles Architecture**: Scoped styles are decomposed into focused submodules under `services/game_session/ui/src/campaigns/styles/` (`base.styles.ts`, `roster.styles.ts`, `modal.styles.ts`, `badge.styles.ts`), composed via `campaignMembersStyles` in `runefoble-campaign-members.styles.ts` (keeping all style modules strictly < 150 lines per Hard Invariant 6).

---

## 10. Gateway Routing for Campaign Routes

The gateway holds no campaign, invite, membership, or session state. Each campaign route verifies the bearer token, then forwards the request and the same `Authorization` value to `game_session`. The gateway never reads a user ID from the body or from a header. The owner checks every object permission (ADR-0015 a, c).

- `game_session` unreachable or not configured: the gateway returns `503` with `{"detail": "Upstream service is unavailable", "upstream": "game_session"}`.
- `game_session` returns a 5xx: the gateway returns `502` with the same body shape.
- `game_session` returns a 4xx (for example `403 permission_denied`, `404 campaign_not_found`, `409 invite_exhausted`): the gateway returns that status and body unchanged.
- An unknown campaign ID returns `404` with `campaign_not_found`. The owner checks existence before permission, so a caller cannot read a fixture campaign for an unknown ID.

## 11. Campaign Detail Hero Header & Metadata Component


The `<runefoble-campaign-header>` component presents the hero banner, campaign title, setting badge, ruleset system pill (`5e`, `PF2e`, `Call of Cthulhu`), active status indicator, DM profile badge, and narrative description:

```typescript
import '@runefoble/game-session-ui/campaigns';

html`
  <runefoble-campaign-header
    .campaign=${campaignItem}
    .canManage=${isDM}
    current-user-id="dm-evelyn"
    @update-campaign=${async (e: CustomEvent<UpdateCampaignPayload>) => {
      const { campaignId, title, setting, system, cover_image_url, description } = e.detail;
      await fetch(\`/api/v1/campaigns/\${campaignId}\`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, setting, system, cover_image_url, description }),
      });
    }}
  ></runefoble-campaign-header>
`;
```

Key features of `<runefoble-campaign-header>`:
- **Hero Banner & Bauhaus Fallback**: Renders high-resolution cover artwork if configured, or automatically renders a vibrant neobrutalist Bauhaus geometric composition with grid patterns and primary-accent shapes when no cover image is provided.
- **Metadata Badges**: Displays formatted system rulesets (`formatRulesetSystem`), setting genre, live status indicator (`Session Live` / `Active`), and DM identity badge.
- **Narrative Lore Block**: Presents the campaign introduction and synopsis with readable line-height and Bauhaus typography tokens.
- **SpiceDB Zanzibar Guarded Editing**: Renders the "Edit Campaign" button strictly when `canManage=true` (granted to users holding `manage` permission in SpiceDB Zanzibar schema).
- **Edit Campaign Modal**: Provides a form to update title, setting, system ruleset, cover art URL, and narrative description, dispatching standard `@update-campaign` custom events with `UpdateCampaignPayload`.
- **Modular Styles Architecture**: Scoped styles are decomposed into focused submodules under `services/game_session/ui/src/campaigns/styles/` (`header_hero.styles.ts`, `header_meta.styles.ts`, `header_actions.styles.ts`), composed via `campaignHeaderStyles` in `runefoble-campaign-header.styles.ts` (keeping all style modules strictly < 150 lines per Hard Invariant 6).


