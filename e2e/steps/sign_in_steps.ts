/**
 * Gherkin steps for real Zitadel sign-in, refusal, and sign-out (TASK-0525, US-0062, ADR-0014).
 *
 * Every step drives the App Shell and the Zitadel hosted login page. No step writes the session or
 * forges a token.
 */

import { expect } from '@playwright/test';
import { Then, When } from '../support/fixtures';
import { API_BASE_URL } from '../support/env';
import { readAppShellSession } from '../support/app_shell_session';
import { findPersona, resolvePersonaKey } from '../support/personas';
import type { HostedLoginOutcome } from '../support/zitadel_login';

const SIGN_IN_BUTTON = 'runefoble-auth-modal button.submit-btn';

When('the visitor opens the sign-in modal and signs in as {string}', async ({ auth, world, page }, roleOrName: string) => {
  world.currentUser = await auth.signInAs(roleOrName, page);
});

When(
  'the visitor opens the sign-in modal and signs in as {string} with the password {string}',
  async ({ auth, world, page }, roleOrName: string, password: string) => {
    const persona = findPersona(resolvePersonaKey(roleOrName));
    const outcome = await auth.attemptSignIn(persona, password, page);
    world.set('hostedLoginOutcome', outcome);
  }
);

Then('Zitadel reports {string}', async ({ world }, expectedMessage: string) => {
  const outcome = world.get<HostedLoginOutcome>('hostedLoginOutcome');
  expect(outcome, 'a sign-in attempt must run first').toBeDefined();
  expect(outcome).toEqual({ kind: 'rejected', message: expectedMessage });
});

Then('the App Shell stores a session for {string}', async ({ page }, roleOrName: string) => {
  const persona = findPersona(resolvePersonaKey(roleOrName));
  const session = await readAppShellSession(page);
  expect(session, 'the App Shell must store a session after Zitadel returns').not.toBeNull();
  expect(session?.user.user_id).toBe(persona.userId);
  expect(session?.tokens.accessToken).toBeTruthy();
});

Then('the top navigation shows the signed-in user', async ({ page, world }) => {
  const userId = world.currentUser?.userId;
  expect(userId, 'a persona must be signed in first').toBeTruthy();
  const userMenu = page.locator('runefoble-user-menu');
  await expect(userMenu).toBeVisible({ timeout: 10_000 });
  await expect(userMenu).toContainText(userId as string);
});

When('the signed-in user signs out from the profile page', async ({ page, auth, world }) => {
  const userId = world.currentUser?.userId;
  expect(userId, 'a persona must be signed in first').toBeTruthy();
  auth.forgetSignedInSession(userId as string);
  await page.goto('#/profile');
  await page.waitForLoadState('domcontentloaded');
  await page.getByRole('button', { name: 'Sign Out', exact: true }).click();
  // Sign-out ends the Zitadel session, then Zitadel returns the browser to the App Shell root.
  await page.waitForURL((url) => url.href.startsWith(`${API_BASE_URL}/`), { timeout: 30_000 });
});

Then('the App Shell holds no session', async ({ page }) => {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await expect
    .poll(async () => readAppShellSession(page), { timeout: 10_000 })
    .toBeNull();
});

Then('the App Shell offers the sign-in modal', async ({ page }) => {
  await page.goto('/#/login');
  await expect(page.locator(SIGN_IN_BUTTON)).toBeVisible({ timeout: 10_000 });
});
