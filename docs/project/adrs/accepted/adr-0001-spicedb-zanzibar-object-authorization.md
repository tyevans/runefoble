# ADR-0001: Zanzibar-Style Fine-Grained Authorization with SpiceDB

## Context

Runefoble is a tabletop roleplaying system where players, game masters (DMs), spectators, and AI agents collaborate on shared state.
Permissions are inherently object-scoped and hierarchical:
- A DM owns the campaign and can manipulate all tokens, notes, and session state.
- A player owns their character sheet and token, but cannot see hidden DM tokens or edit other players' sheets.
- An AI stand-in acts on behalf of an absent player with delegated permissions granted by the DM.
- Spectators can observe the live board, but cannot move tokens or trigger dice rolls.

Role-Based Access Control (RBAC) fails in this domain because roles depend entirely on the specific campaign, session, and character instance. A user is a DM in Campaign A, a player in Campaign B, and an invited spectator in Campaign C.

## Decision

We adopt **SpiceDB** (Google Zanzibar-inspired authorization system) as our authorization engine.

1. **Object-Level Scoping**: Permissions are evaluated as relationship graph tuples (`resource:id#relation@subject:id`).
2. **Standardized Schema**: We maintain a canonical schema at `libs/runefoble_auth/schema/runefoble.zed`.
3. **Self-Hosted Deployment**: SpiceDB runs as a containerized service backed by PostgreSQL in our Kubernetes stack.
4. **Decoupled AuthN and AuthZ**: Zitadel verifies identity and issues OIDC JWTs. SpiceDB evaluates whether that identity is authorized to execute an action on a target resource.

## Consequences

- Fine-grained rules (e.g. allowing an AI stand-in to move an absent player's token) are expressed directly in Zanzibar schema without service code changes.
- Authorization checks are sub-millisecond graph evaluations.
- Developers must write SpiceDB relationship tuples whenever entities (campaigns, characters, tokens) are created or reassigned.
