/**
 * Runefoble authentication fixtures for the Playwright BDD suite (TASK-0525, ADR-0014, ADR-0015 d).
 *
 * Every signed-in persona comes from a real Zitadel OIDC sign-in in the browser. The suite never forges
 * a token. The first sign-in of a persona in a worker runs the hosted login. Later scenarios in the same
 * worker restore the session that Zitadel issued during that first sign-in. The session lives in worker
 * memory only. It is never written to disk.
 */

import type { Page } from '@playwright/test';
import type { TestUser } from './world';
import { findPersona, PERSONA_SEEDS, resolvePersonaKey, type PersonaKey, type PersonaRecord } from './personas';
import { APP_SHELL_SESSION_KEY, readAppShellSession, type AppShellSession } from './app_shell_session';
import { signInWithZitadel, type HostedLoginOutcome } from './zitadel_login';

/** Raw App Shell session JSON per persona, as Zitadel issued it during this worker's first sign-in. */
const issuedSessions = new Map<PersonaKey, string>();

/** Keeps a token margin, so a restored session does not expire in the middle of a scenario. */
const MIN_REMAINING_MS = 60_000;

function isUsable(raw: string): boolean {
  const session = JSON.parse(raw) as AppShellSession;
  return session.tokens.expiresAt - Date.now() > MIN_REMAINING_MS;
}

export class AuthFixtures {
  constructor(private page: Page) {}

  /** Signs the persona in through Zitadel in the given page (default: the test page). */
  async signInAs(roleOrName: string, targetPage: Page = this.page): Promise<TestUser> {
    const persona = findPersona(resolvePersonaKey(roleOrName));
    const issued = issuedSessions.get(persona.key);
    if (issued !== undefined && isUsable(issued)) {
      await this.restoreSession(targetPage, issued);
    } else {
      await this.signInThroughZitadel(persona, targetPage);
    }

    const session = await readAppShellSession(targetPage);
    if (!session) {
      throw new Error(`The App Shell stored no session for persona "${persona.key}".`);
    }
    if (session.user.user_id !== persona.userId) {
      throw new Error(
        `The App Shell session belongs to "${session.user.user_id}", not to persona "${persona.key}".`
      );
    }
    const seed = PERSONA_SEEDS[persona.key];
    return {
      userId: persona.userId,
      username: `${seed.givenName} ${seed.familyName}`,
      token: session.tokens.accessToken,
    };
  }

  /** Submits a password through the Zitadel page and reports Zitadel's answer. Used for refusal scenarios. */
  async attemptSignIn(persona: PersonaRecord, password: string, targetPage: Page = this.page): Promise<HostedLoginOutcome> {
    await clearBrowserState(targetPage);
    return signInWithZitadel(targetPage, persona.loginName, password);
  }

  /** Drops the stored session of a persona after it signs out, so later scenarios sign in again. */
  forgetSignedInSession(userId: string): void {
    for (const [key, raw] of issuedSessions) {
      if (JSON.parse(raw).user.user_id === userId) issuedSessions.delete(key);
    }
  }

  private async signInThroughZitadel(persona: PersonaRecord, targetPage: Page): Promise<void> {
    await clearBrowserState(targetPage);
    const outcome = await signInWithZitadel(targetPage, persona.loginName, persona.password);
    if (outcome.kind !== 'session') {
      throw new Error(`Zitadel refused persona "${persona.key}": ${outcome.message}`);
    }
    const raw = await targetPage.evaluate((key) => window.localStorage.getItem(key), APP_SHELL_SESSION_KEY);
    if (raw === null) {
      throw new Error(`The App Shell stored no session for persona "${persona.key}".`);
    }
    issuedSessions.set(persona.key, raw);
  }

  /** Puts a session that Zitadel issued earlier in this worker into the App Shell storage. */
  private async restoreSession(targetPage: Page, raw: string): Promise<void> {
    // Write the storage from a plain same-origin document. Loading the App Shell first would run its
    // route guard, which opens the sign-in modal and keeps it open after the restore.
    await targetPage.goto('/runtime-config.json');
    await targetPage.evaluate(
      ([key, value]) => window.localStorage.setItem(key, value),
      [APP_SHELL_SESSION_KEY, raw] as const
    );
    await targetPage.goto('/#/campaigns');
  }
}

/** Starts from a state with no Zitadel cookies and no App Shell storage, so the login page is shown. */
async function clearBrowserState(targetPage: Page): Promise<void> {
  await targetPage.context().clearCookies();
  await targetPage.goto('/#/login');
  await targetPage.evaluate(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });
  await targetPage.reload();
}
