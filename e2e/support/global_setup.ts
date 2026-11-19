/**
 * Playwright global setup: creates this run's test personas in Zitadel (TASK-0525, ADR-0014).
 *
 * Usernames carry a per-run suffix, so runs do not collide. The registry (including the generated
 * passwords) lives in one process environment variable. Nothing is written to disk.
 */

import { randomBytes } from 'node:crypto';
import { APP_BASE_URL } from './environment';
import { PERSONA_KEYS, PERSONA_REGISTRY_ENV, PERSONA_SEEDS, type PersonaRecord } from './personas';
import { createHumanUser, fetchIssuer, readAdminPat } from './zitadel_admin';

function newRunSuffix(): string {
  return `${Date.now().toString(36)}${randomBytes(3).toString('hex')}`;
}

function newPassword(): string {
  // Covers Zitadel's default policy: upper case, lower case, digits, and a symbol.
  return `Aa1!${randomBytes(12).toString('hex')}`;
}

export default async function globalSetup(): Promise<void> {
  const pat = readAdminPat();
  const issuer = await fetchIssuer(APP_BASE_URL);
  const suffix = newRunSuffix();

  const registry: PersonaRecord[] = [];
  for (const key of PERSONA_KEYS) {
    const seed = PERSONA_SEEDS[key];
    const username = `${key}-${suffix}`;
    const password = newPassword();
    const userId = await createHumanUser(issuer, pat, {
      username,
      givenName: seed.givenName,
      familyName: seed.familyName,
      email: `${username}@example.test`,
      password,
    });
    registry.push({ key, userId, loginName: username, password });
  }

  process.env[PERSONA_REGISTRY_ENV] = JSON.stringify(registry);
}
