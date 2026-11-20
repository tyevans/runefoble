# ADR-0023: A Campaign Invite Link Creates the Player Account

## Status
Accepted (2026-11-19). The user chose this option for release one (PRD-0025): a private, invite-only group in which the invite link also creates the account.

## Context
PRD-0025 makes release one invite-only. ADR-0015 (d) says that new users register through the Zitadel hosted sign-up page, and that no in-app sign-up form exists.

Zitadel self-registration is open to anyone who finds the domain. Zitadel cannot easily limit it to people who hold a campaign invite. A stranger could register, create campaigns, and use the GPU host.

Options considered:

- **Option A. The admin creates each account in Zitadel.** It is closed, but each new player needs the admin first.
- **Option B. Open self-registration.** It is easy, but not invite-only.
- **Option C. The invite link creates the account.** A person who holds a valid invite gives a name and an email. Runefoble asks Zitadel to create the user. Zitadel sends its own email to verify the address and set a password.

## Decision
Use **Option C**. This decision replaces the second rule of ADR-0015 (d) for release one. The other rules of ADR-0015 (d) stay: sign-in uses the OIDC authorization-code flow with PKCE, and no Zitadel role grants a SpiceDB relation.

### (a) Zitadel self-registration is off
The hosted profile turns off self-registration in Zitadel. The only ways to get an account are a campaign invite and the Zitadel admin console.

### (b) Runefoble never handles a password
The account route takes a display name and an email only. Zitadel creates the user with no password and sends its initialization email. The person sets the password on the Zitadel hosted page and verifies the email there. Runefoble never sees, stores, or sends a password or a Zitadel init code.

### (c) game_session owns redemption, and a port owns the Zitadel call
`game_session` owns invites and membership (ADR-0015 (a)). It validates the invite and records a pending join for the new user. An `AccountProvisioner` port in `libs/runefoble_auth` creates the Zitadel user. Its adapter calls the Zitadel Management API with a service account credential from a Kubernetes Secret (ADR-0015 (e)). The gateway only forwards the route (ADR-0015 (b)). When Zitadel is unavailable, the route returns 503 and creates nothing (ADR-0015, no hidden fallbacks).

### (d) An invite is a limited bearer credential
- An invite has an expiry and a maximum number of uses. Each created account uses one. An expired or used-up invite returns 410.
- The route is rate limited for each invite and for each client address.
- The route answers the same way for an email that already has an account and for a new email. Zitadel then sends a sign-in email instead of an init email, so the route does not show which emails exist.
- An account created through an invite gets no campaign relation until that person signs in. The first sign-in completes the pending join, and only then does SpiceDB get the `player` relation (Hard Invariant 1).
- The DM sees each pending and completed join in the member list and can remove a member.

### (e) Sign-in completes the join
After the person sets a password and signs in, the App Shell returns to `#/join/<token>`. The join route sees the pending join for that user and completes it.

## Consequences

- **Positive**:
  - Release one stays invite-only, and a friend needs only the link.
  - Passwords, verification and recovery stay in Zitadel.
- **Negative**:
  - Runefoble holds a Zitadel service account that can create users. Its Secret needs the same care as the database password.
  - A leaked invite link lets strangers create accounts up to the use limit. The expiry, the use limit and DM removal bound this risk.
- **Follow-up**: TASK-0967 implements (b) to (e). TASK-0950 (join view) and TASK-0958 (Zitadel hosted settings) are updated for (a) and (e).

## References

- ADR-0015: Audit Remediation Decisions, decisions (a), (b), (d) and (e).
- ADR-0001: SpiceDB Zanzibar object authorization.
- PRD-0025: Voice-First Release One for a Private Group.
- `docs/reference/identity-and-token-contract.md`.
