# Explanation: Zanzibar-Style Object Authorization in Tabletop Gaming

## Why Role-Based Access Control (RBAC) Breaks Down
In a multi-campaign virtual tabletop platform, users wear different hats depending on the entity:
- User Alice is the **Dungeon Master** in Campaign 1. She should be able to view hidden monsters, drag any token, and edit any player sheet.
- User Alice is a **Player** in Campaign 2, controlling only her character "Valeros". She must not view the DM's secret maps or manipulate Bob's character.
- User Bob is absent in Campaign 2, but has granted **AI Stand-in Delegation** to The Watcher to move his token.
- User Charlie is an **Invited Spectator** in Campaign 2, allowed to view the board stream, but denied permission to move tokens or roll dice.

A static role like `"admin"` or `"player"` cannot express these dynamic, object-scoped relationships.

## Google Zanzibar and SpiceDB
Google Zanzibar models authorization as a directed graph of relationships:
`resource#relation@subject`

In Runefoble:
1. **Campaign Hierarchy**:
   `campaign:c1#owner@user:alice`
   `campaign:c1#player@user:bob`
2. **Object Scoping**:
   `character:valeros#owner@user:alice`
   `character:valeros#campaign@campaign:c1`
3. **Recursive Permission Rules**:
   A user can move a board token if:
   - They own the associated character (`character->owner`), OR
   - They are the DM/owner of the parent campaign (`campaign->run_session`).

This architecture delivers sub-millisecond, cryptographically auditable authorization checks that scale across millions of campaigns and entities.
