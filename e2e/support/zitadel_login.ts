/**
 * Drives the Zitadel hosted login page from the App Shell sign-in modal (TASK-0525, ADR-0014).
 *
 * The browser enters the password on Zitadel only. The App Shell never sees it (ADR-0015 d).
 * Selectors match the Zitadel v2.x login UI: #loginName, #password, #submit-button, .lgn-error-message.
 */

import type { Page } from '@playwright/test';
import { APP_BASE_URL } from './environment';
import { APP_SHELL_SESSION_KEY } from './app_shell_session';

export type HostedLoginOutcome = { kind: 'session' } | { kind: 'rejected'; message: string };

const LOGIN_TIMEOUT_MS = 120_000;
const SIGN_IN_BUTTON = 'runefoble-auth-modal button.submit-btn';
const ERROR_MESSAGE = '.lgn-error-message';

/** Starts at the App Shell sign-in modal, completes the Zitadel form, and reports what the browser ended with. */
export async function signInWithZitadel(page: Page, loginName: string, password: string): Promise<HostedLoginOutcome> {
  await page.locator(SIGN_IN_BUTTON).click();
  await page.waitForURL((url) => url.pathname.startsWith('/ui/login/'), { timeout: 30_000 });

  await page.locator('#loginName').fill(loginName);
  await page.locator('#submit-button').click();

  await page.locator('#password').fill(password);
  await page.locator('#submit-button').click();

  return waitForOutcome(page);
}

async function waitForOutcome(page: Page): Promise<HostedLoginOutcome> {
  const deadline = Date.now() + LOGIN_TIMEOUT_MS;
  while (Date.now() < deadline) {
    const error = page.locator(ERROR_MESSAGE);
    if (await error.isVisible()) {
      return { kind: 'rejected', message: (await error.innerText()).trim() };
    }
    if (page.url().startsWith(`${APP_BASE_URL}/`)) {
      await page.waitForFunction((key) => window.localStorage.getItem(key) !== null, APP_SHELL_SESSION_KEY, {
        timeout: 15_000,
      });
      return { kind: 'session' };
    }
    // First sign-in of a user can ask for a second factor. The suite skips that prompt.
    const skip = page.getByRole('button', { name: 'Skip' });
    if (await skip.isVisible()) {
      await skip.click();
    }
    await page.waitForTimeout(250);
  }
  const pageText = (await page.locator('body').innerText().catch(() => '')).replace(/\s+/g, ' ').slice(0, 200);
  throw new Error(
    `Zitadel sign-in did not finish within ${LOGIN_TIMEOUT_MS} ms. Last URL: ${page.url()}. Page text: "${pageText}"`
  );
}
