/**
 * Zitadel management API client for the e2e global setup (TASK-0525, ADR-0014, Hard Invariant 7).
 *
 * Personas are created only through this public API. No database is touched.
 * The admin personal access token comes from the environment and never reaches a file, a log, or an error message.
 */

import { ZITADEL_ADMIN_PAT_ENV } from './environment';

export interface HumanUserInput {
  username: string;
  givenName: string;
  familyName: string;
  email: string;
  password: string;
}

/** Reads the admin token from the environment. The caller must not print it. */
export function readAdminPat(): string {
  const pat = process.env[ZITADEL_ADMIN_PAT_ENV];
  if (!pat) {
    throw new Error(
      `${ZITADEL_ADMIN_PAT_ENV} is not set. Run the suite through make test-e2e, which reads the token from the cluster.`
    );
  }
  return pat;
}

/** Removes every occurrence of the token from a message before the message is thrown or logged. */
export function maskSecret(message: string, secret: string): string {
  return secret ? message.split(secret).join('<redacted>') : message;
}

/** Reads the browser-facing issuer that the App Shell uses (runtime config, TASK-0526). */
export async function fetchIssuer(appBaseUrl: string): Promise<string> {
  const res = await fetch(`${appBaseUrl}/runtime-config.json`);
  if (!res.ok) {
    throw new Error(`Runtime config request failed with status ${res.status}.`);
  }
  const config = (await res.json()) as { issuer?: unknown };
  if (typeof config.issuer !== 'string' || config.issuer.length === 0) {
    throw new Error('Runtime config has no issuer.');
  }
  return config.issuer.replace(/\/$/, '');
}

/** Creates a verified human user with a password. Returns the Zitadel user id. */
export async function createHumanUser(issuer: string, pat: string, input: HumanUserInput): Promise<string> {
  const res = await fetch(`${issuer}/v2beta/users/human`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${pat}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      username: input.username,
      profile: {
        givenName: input.givenName,
        familyName: input.familyName,
        displayName: `${input.givenName} ${input.familyName}`,
      },
      email: { email: input.email, isVerified: true },
      password: { password: input.password, changeRequired: false },
    }),
  });
  const body = await res.text();
  if (!res.ok) {
    throw new Error(
      maskSecret(`Zitadel refused to create user "${input.username}": ${res.status} ${body.slice(0, 300)}`, pat)
    );
  }
  const parsed = JSON.parse(body) as { userId?: unknown };
  if (typeof parsed.userId !== 'string' || parsed.userId.length === 0) {
    throw new Error(`Zitadel returned no user id for "${input.username}".`);
  }
  return parsed.userId;
}
