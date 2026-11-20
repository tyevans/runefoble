/**
 * Session View Controls Step Definitions (TASK-0954).
 *
 * The steps read what the player sees: the stance drawer status, the stance that the server
 * kept after a reload, and the DM trap controls. A save is confirmed by its gateway response
 * before the step returns, so a reload never races the write. Governed by ADR-0014, ADR-0015 and
 * Hard Invariant 7.
 */

import { expect, type Page } from '@playwright/test';
import { Then, When } from '../support/fixtures';
import type { World } from '../support/world';

const DRAWER = 'runefoble-absentee-directive';
const TRAP_CONTROLS = 'runefoble-dm-trap-controls';
const GUARDRAILS_PATH = /\/api\/v1\/characters\/[^/]+\/guardrails$/;

/** Opens the stance drawer from the session view and waits until the drawer is drawn. */
async function openStanceDrawer(page: Page, label: string): Promise<void> {
  const button = page.getByRole('button', { name: label });
  await expect(button, `"${label}" must be shown in the session view`).toHaveCount(1, { timeout: 15_000 });
  await button.click();
  await expect(page.locator(DRAWER)).toBeVisible({ timeout: 10_000 });
}

When(/^(\w+) opens "([^"]+)"(?: from (?:her|his) session view)?$/, async ({ world }, persona: string, label: string) => {
  await openStanceDrawer(world.getPage(persona.toLowerCase()), label);
});

Then('the status of the stance drawer of {word} reads {string}', async ({ world }, persona: string, status: string) => {
  const page = world.getPage(persona.toLowerCase());
  await expect(page.locator(`${DRAWER} .status-pill`)).toHaveText(status, { timeout: 10_000 });
});

When('{word} selects the stance {string}', async ({ world }, persona: string, stance: string) => {
  const page = world.getPage(persona.toLowerCase());
  const saved = page.waitForResponse(
    (response) => response.request().method() === 'PUT' && GUARDRAILS_PATH.test(new URL(response.url()).pathname),
    { timeout: 15_000 }
  );
  await page.locator(`${DRAWER} .stance-btn`, { hasText: stance }).click();
  const answer = await saved;
  expect(answer.ok(), `The stance save answered ${answer.status()}`).toBe(true);
});

Then('the selected stance of {word} is {string}', async ({ world }, persona: string, stance: string) => {
  const page = world.getPage(persona.toLowerCase());
  await expect(page.locator(`${DRAWER} .stance-btn[aria-checked="true"] .stance-name`)).toHaveText(stance, {
    timeout: 10_000,
  });
});

Then('no {string} button is shown to {word}', async ({ world }, label: string, persona: string) => {
  const page = world.getPage(persona.toLowerCase());
  await expect(page.getByRole('button', { name: label })).toHaveCount(0, { timeout: 10_000 });
});

Then('no {string} layer toggle is shown', async ({ world }, state: string) => {
  const controls = world.getPage('evelyn').locator(TRAP_CONTROLS);
  await expect(controls.locator('button', { hasText: state })).toHaveCount(0, { timeout: 10_000 });
});

Then('the {string} control is shown', async ({ world }, label: string) => {
  const controls = world.getPage('evelyn').locator(TRAP_CONTROLS);
  await expect(controls.getByRole('button', { name: label })).toHaveCount(1, { timeout: 10_000 });
});
