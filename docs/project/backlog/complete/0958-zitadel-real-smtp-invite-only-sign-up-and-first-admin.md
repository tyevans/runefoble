---
id: '0958'
title: Zitadel Uses Real SMTP, Closed Registration, and a First Admin on the Public Domain
status: Complete
created: 2026-11-19
dependencies:
- '0955'
- '0957'
- '0959'
governing_adrs:
- ADR-0005
- ADR-0015
governing_prds:
- PRD-0025
governing_stories: []
target_bc: core
target_release: 1.0.0
---

# TASK-0958: Zitadel Uses Real SMTP, Closed Registration, and a First Admin on the Public Domain

## Status

Complete

## Summary

Zitadel sends real e-mail through an operator-chosen SMTP server. Public registration turns off, so only accounts that the first admin creates can sign in. The public auth host, HTTPS issuer, and HTTPS redirect URIs come from values. The development bootstrap flag turns off.

## Problem Statement

- `deployments/helm/runefoble/templates/zitadel.yaml:131-134` wires SMTP only when `mailpit.enabled` is true, to host `mailpit:1025`.
- `zitadel.yaml:134-137` sets an empty SMTP user and password. `zitadel.yaml:141-142` sets TLS to `false`. `zitadel.yaml:147-149` turns off the sender-domain check.
- `values.yaml` has no key for SMTP host, port, TLS, user, password, or sender (search found none).
- `values.yaml:197-199` sets `externalDomain: auth.localhost`, `externalPort: 80`, and `externalSecure: false`. `zitadel.yaml:80-85` passes these to Zitadel.
- `values.yaml:219-222` sets redirect URIs to `http://localhost/...`. `values.yaml:224` sets `devMode: true`. `deployments/zitadel_bootstrap/src/zitadel_bootstrap/job.py:69-71` passes both to the provisioning step.
- No login-policy step exists in the bootstrap code. A search of `deployments/zitadel_bootstrap/src/` finds no login-policy call. The chart therefore leaves the Zitadel default login policy in place. Confirm in the live test (Frontdoor Blackbox Test Plan) whether a visitor can register.
- `values.yaml:200` sets the admin e-mail to `admin@runefoble.local`. `zitadel.yaml:118-130` creates the human admin on first start.
- `values.yaml:212-214` sets the bootstrap machine user's PAT expiry to `2099-01-01`. `zitadel.yaml:116-117` sets the expiry on first start only. After the PAT expires, the bootstrap Job cannot run on upgrade.

## Documentation & Architecture Review

- ADR-0015 (d): new users register through the Zitadel sign-up page. No in-app sign-up form exists. This record closes the sign-up page for this release. It does not add a form.
- ADR-0015 (c): every service verifies Zitadel tokens. The issuer must match the public host (`templates/_helpers.tpl:5-15`).
- `docs/how-to/authenticate-with-zitadel-oidc.md`: the bootstrap contract. Update it with the new HTTPS values and the login policy step.
- Zitadel reference: the login-policy field `allow_register` turns off local registration. Zitadel's advisory 10001 states that it affects local registration only. Federated sign-in can still create accounts. Check the advisory before you rely on it (source: `https://github.com/zitadel/zitadel/blob/main/apps/docs/content/support/advisory/a10001.mdx`).

## Product & User Story References

- PRD-0025, "What good looks like" 1 (friends sign up and join through the invite link) and 8 (real e-mail, private credentials, invite-only sign-up).
- PRD-0025 uses the word "sign up" for the players. Under closed registration, the admin creates their accounts. The PRD text must change (see input D12).
- No user story. This is platform work.

## Detailed Specification & Implementation Plan

1. SMTP values. Read these keys in the template with `default`. Set them in the hosted example (0955). Do not add them to `values.yaml`.
   ```
   zitadel:
     smtp:
       host: ""                  # SMTP host name (input D4)
       port: 587                 # SMTP port (input D4)
       tls: true                 # STARTTLS or implicit TLS, per the provider (input D4)
       user: ""                  # SMTP login name (input D4)
       passwordSecretKey: smtp-password   # key in the credentials Secret (record 0959)
       fromAddress: ""           # sender address (input D4)
       fromName: Runefoble
   ```
2. In `zitadel.yaml`, render the SMTP block when `mailpit.enabled` is true (dev) or when `zitadel.smtp.host` is set. The host, port, TLS, user, and sender come from values. The password comes from `secretKeyRef` (Secret key from `passwordSecretKey`). It is never a plain value. The check `SMTPSENDERADDRESSMATCHESINSTANCEDOMAIN` is set from a value. Its default is `false`.
3. Hosted public settings in the example:
   - `zitadel.externalDomain` is the public auth host (input D1); `externalPort: 443`; `externalSecure: true`.
   - `zitadel.bootstrap.redirectUris` and `postLogoutRedirectUris` use `https://` and the public App Shell host.
   - `zitadel.bootstrap.devMode: false`.
   - `zitadel.adminEmail` is the first admin (input D7).
4. Closed registration. Add a provisioning step to `deployments/zitadel_bootstrap/src/zitadel_bootstrap/provisioning.py`. It sets the instance default login policy `allow_register` to `false` through the Zitadel admin API. The step is idempotent. The Job fails when Zitadel refuses the call. It never skips the step silently. The change must not turn off federated sign-in unless input D12 says so.
5. PAT expiry. Keep `patExpirationDate` as a value. The record sets no default for the hosted profile. The runbook (0965) owns the rotation steps. The machine user's PAT is created on first start only (`zitadel.yaml:116-117`). Each upgrade needs a valid PAT. Input D12b sets the expiry and the rotation plan.
6. Keep local rendering unchanged. The SMTP block stays for Mailpit in local mode.

Rules for this record:
- Do not add lines to `values.yaml`.
- Do not send the SMTP password as an environment value or in a command.

### Inputs (user decisions)

- D1: public auth host name.
- D4: SMTP provider, host, port, TLS mode, login name, and sender address. The password goes into the Secret (0959).
- D7: first admin e-mail address and the person who runs the first sign-in.
- D12: how members get accounts. Option A: the admin creates each account in Zitadel, and Zitadel sends the setup e-mail. Option B: keep self-registration open, which is not invite-only. This record implements A.
- D12b: PAT expiry and rotation owner. The runbook (0965) gets the steps.

## ADR-0023 Update (2026-11-19)

The hosted profile turns Zitadel self-registration off (ADR-0023 (a)). The only ways to get an account are a campaign invite (TASK-0967) and the Zitadel admin console. The first admin is created by the bootstrap in this task. Test: `helm template` with the hosted values renders the login policy with registration off.

## Frontdoor Blackbox Test Plan

Render tests in a new file `tests/test_blackbox_helm_zitadel_hosted.py`:
- Hosted render: the Zitadel container has `ZITADEL_EXTERNALSECURE` `"true"`, `ZITADEL_EXTERNALPORT` `"443"`, and the SMTP host from the value. The SMTP password variable reads `secretKeyRef` with key `smtp-password`.
- Hosted render: no string `mailpit` appears in the Zitadel pod spec.
- Hosted render: the bootstrap Job has `RUNEFOBLE_ZITADEL_DEV_MODE` `"false"` and only `https://` redirect URIs.
- Local render: the Mailpit SMTP values are unchanged.

Live tests (new Playwright scenarios, Hard Invariant 7, UI only, no database access):
- A visitor opens the sign-in page on the public host. No "create account" link appears, and the registration URL shows Zitadel's refusal.
- The admin signs in with the first admin account. The admin creates a member account through the Zitadel console. The member receives the setup e-mail. Test this on Mailpit in the dev profile and on the real provider in a staging run. Tag the staging run `@requires-smtp`.

## Definition of Done

- Render tests pass. The provisioning step has a test against a live Zitadel container in the Kind smoke job (0964). It does not mock the Zitadel client.
- `docs/how-to/authenticate-with-zitadel-oidc.md` describes the HTTPS values and the closed registration.
- The Playwright scenario for the closed registration passes in the 0964 smoke job.
- Decision D12 is recorded in `docs/reference/hosted-profile.md`.
- `CHANGELOG.md` `[Unreleased]` entry. Recorded at merge.

## Audit Provenance

- Severity: high (no real e-mail; a stranger can register).
- Source audits: `.audit/research/r1-hosting.md`, sections 4 and 11 (D4, D7). Lines were checked against `main` at `33885a70`. The research says the bootstrap Job is a hook at `zitadel-bootstrap.yaml:8`. The hook annotation is at `zitadel-bootstrap.yaml:66` (post-install and post-upgrade).
