# ADR-0015: Audit Remediation Decisions

## Status
Accepted

## Context
A platform audit (2026-11-17) found five structural problems. Each problem breaks a Hard Invariant or a Definition of Ready rule:

1. **Gateway holds domain state.** The API gateway stores campaigns, invites, memberships, and character wardrobe data in memory. It also returns canned payloads when an upstream service fails. Hard Invariant 2 and the zero-shim rule (DoR 9) do not allow this.
2. **Services trust the gateway, not the token.** Some services accept identity from headers or claims that the gateway sets. A service that does not verify the token itself is exposed if the gateway is bypassed.
3. **Authorization uses role names.** Claim sync maps Zitadel roles to SpiceDB relations. Hard Invariant 1 forbids role checks in business logic.
4. **Fallbacks hide failures.** In-memory event stores, mock providers, and in-process package imports run in deployed environments. A failed dependency looks like a working one.
5. **Service-to-service calls have no credential.** Internal calls, such as from The Watcher to the inference worker, are not authenticated.

## Decision
We adopt the following decisions. They apply to all new and existing refined tasks in `docs/project/backlog/`.

### (a) Campaign lifecycle and membership belong to game_session
- `game_session` owns campaign lifecycle, invite tokens, and party membership. It is the only service that writes these states.
- The gateway holds no domain state. It does not store campaigns, invites, memberships, or grants.
- The `game_session#campaign` relation in `runefoble.zed` is the authoritative link between a session and its campaign.

### (b) The gateway is thin
- The gateway performs three tasks only: authentication, routing, and aggregation.
- All calls to upstream services go through one shared, typed service client in `libs/`.
- The gateway returns no canned or fallback payloads.
- When an upstream service fails, the gateway returns `502 Bad Gateway` or `503 Service Unavailable`. It never returns a substitute value.

### (c) Every service verifies Zitadel JWTs itself
- Every HTTP route and every WebSocket connection in every service verifies the Zitadel JWT. This is defense in depth. A service does not trust identity headers set by the gateway.
- WebSocket clients send the token in the `Sec-WebSocket-Protocol` subprotocol. The token must never appear in the query string, because query strings are written to logs.
- Development mode that skips token checks is off by default. If it is enabled by mistake, the service fails closed and refuses to start in deployed environments.

### (d) Registration and sign-in use Zitadel
- New users register through the Zitadel hosted sign-up page.
- The client signs in with the OIDC authorization-code flow and PKCE. No in-app sign-up form exists.
- ADR-0023 (2026-11-19) changes the first rule for release one: Zitadel self-registration is off, and a campaign invite link creates the account through Zitadel. Runefoble still handles no password.
- Claim sync based on roles is removed. No Zitadel role grants a SpiceDB relation. Authorization checks use only the relations in `runefoble.zed` (Hard Invariant 1).

### (e) Service-to-service calls use a Kubernetes Secret credential
- A service that calls another service presents a service credential. The credential is stored in a Kubernetes Secret and mounted into the calling pod.
- The receiving service rejects calls that do not present a valid credential.
- Example: The Watcher calls the inference worker with this credential.

### (f) The PostgreSQL event store is mandatory in deployed environments
- Every deployed service uses the PostgreSQL event store. The service fails fast at startup if the store is not configured.
- The in-memory event store is for tests only. Production code paths must not select it.

## Consequences

- **Positive**:
  - Each domain state has one owner. Changes to campaigns, invites, and membership follow one path.
  - Failures are visible. A broken upstream service returns an error, not a false success.
  - A bypassed gateway cannot reach service data without a valid token.
  - Role names no longer grant access. Access follows the SpiceDB schema only.
  - Service calls are authenticated inside the cluster.
- **Negative**:
  - Local development needs the Zitadel and PostgreSQL containers. Developers cannot run services with the in-memory store.
  - Each service fetches Zitadel signing keys (JWKS). This adds one network call per key rotation.
  - Some existing tasks change scope or dependencies. These are recorded in the audit index and in the task files.
- **Follow-up**: Tasks 0520 to 0560 implement these decisions. Task 0625 removes the hardcoded SpiceDB key defaults. Task 0590 implements decision (a).

## References
- [`adr-0001-spicedb-zanzibar-object-authorization.md`](adr-0001-spicedb-zanzibar-object-authorization.md)
- [`adr-0014-bdd-gherkin-user-stories-and-playwright-e2e.md`](adr-0014-bdd-gherkin-user-stories-and-playwright-e2e.md)
- AGENTS.md, Hard Invariants 1, 2, and 7, and Definition of Ready rule 9.
- [`docs/reference/identifiers-and-uuid-policy.md`](../../reference/identifiers-and-uuid-policy.md): UUID policy for client ids (TASK-0816).
