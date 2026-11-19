/**
 * Character Sheet and Inventory Mutations Playwright BDD Step Definitions
 *
 * Implements blackbox frontdoor UI interactions for character creation,
 * builder modal, sheet inspection, HP deltas, equipment/inventory,
 * stand-in tactical guardrails, and page reload persistence.
 * Governed by ADR-0002, ADR-0004, ADR-0013, ADR-0014, and Hard Invariant 7.
 */

import { expect, type Page } from '@playwright/test';
import { Given, When, Then } from '../support/fixtures';
import type { World } from '../support/world';
import type { AuthFixtures } from '../support/auth_fixtures';
import { bearerHeader, type FrontdoorApi } from '../support/frontdoor_api';
import { API_BASE_URL } from '../support/env';
import { assertOk, exactText, requireValue } from '../support/guards';

const SHEET = 'runefoble-character-sheet';

/** The Hit Points value, for example "33 / 38". */
function hitPointsValue(page: Page) {
  return page
    .locator(`${SHEET} .vital-card`)
    .filter({ has: page.locator('.vital-label', { hasText: exactText('Hit Points') }) })
    .locator('.vital-val');
}

/** Matches a Hit Points value whose current HP is exactly `hp`. */
function currentHpText(hp: number): RegExp {
  return new RegExp(`^\\s*${hp}\\s*/`);
}

function mainHandSlot(page: Page) {
  return page
    .locator(`${SHEET} .equip-slot`)
    .filter({ has: page.locator('.slot-label', { hasText: 'Main Hand' }) });
}

/** The roster card of the character that this scenario created. */
function createdCharacterCard(page: Page, world: World) {
  const id = requireValue(world.characterId, 'No character id. Create the character in this scenario first.');
  return page.locator(`runefoble-character-roster article.character-card[data-character-id="${id}"]`);
}

/**
 * Ensures user is authenticated and navigating the character sheet
 * for isolated scenario execution.
 */
async function ensureOnCharacterSheet(
  page: Page,
  world: World,
  auth: AuthFixtures,
  frontdoorApi: FrontdoorApi,
  expectedName = 'Thorne Ironbreaker'
): Promise<string> {
  if (!world.currentUser) {
    const user = await auth.signInAs('Marcus');
    world.currentUser = user;
  }

  const currentUrl = page.url();
  const isOnSheet = currentUrl.includes('#/characters/') && currentUrl.split('#/characters/')[1];

  if (isOnSheet && world.characterId) {
    await page.waitForSelector('runefoble-character-sheet', { timeout: 15_000 });
    return world.characterId;
  }

  let charId = world.characterId;
  if (!charId) {
    // Setup goes through the public characters route. A failed call throws with the response body.
    const created = await frontdoorApi.createCharacter(
      {
        name: expectedName,
        characterClass: 'Fighter',
        level: 4,
        maxHp: 38,
        currentHp: 38,
        armorClass: 18,
        speed: 30,
      },
      requireValue(world.currentUser.token, 'No access token. Sign the player in before character setup.')
    );
    charId = requireValue<string>(created.id, 'The character reply has no id.');
    world.characterId = charId;
  }

  await page.goto(`#/characters/${charId}`);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForSelector('runefoble-character-sheet', { timeout: 15_000 });
  return charId;
}

Given(
  'an authenticated player {string}',
  async ({ auth, world }, personaName: string) => {
    const user = await auth.signInAs(personaName);
    world.currentUser = user;
  }
);

When(
  '{word} opens the character roster and clicks "+ Create Character"',
  async ({ page, world, auth }, _persona: string) => {
    if (!world.currentUser) {
      const user = await auth.signInAs('Marcus');
      world.currentUser = user;
    }

    await page.goto('#/characters');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForSelector('runefoble-character-roster', { timeout: 15_000 });

    const createBtn = page.locator('runefoble-character-roster #create-char-btn');

    await expect(createBtn).toBeVisible({ timeout: 15_000 });
    await createBtn.click();
    await page.waitForSelector('runefoble-character-builder-modal .modal-dialog', { timeout: 15_000 });
  }
);

When(
  'fills in name {string}, class {string}, and level {int}',
  async ({ page, world }, charName: string, charClass: string, level: number) => {
    world.set('characterName', charName);

    const modal = page.locator('runefoble-character-builder-modal');
    await expect(modal.locator('.modal-dialog')).toBeVisible({ timeout: 10_000 });

    const nameInput = modal.locator('#char-name');
    await nameInput.fill(charName);

    const classSelect = modal.locator('#char-class');
    await classSelect.selectOption(charClass);

    const levelInput = modal.locator('#char-level');
    await levelInput.fill(String(level));

    const hpInput = modal.locator('#char-hp');
    await hpInput.fill('38');

    // Read the id of the new character from the reply to the UI's own create call.
    const createReply = page.waitForResponse(
      (res) => res.request().method() === 'POST' && new URL(res.url()).pathname === '/api/v1/characters'
    );
    const submitBtn = modal.locator('button.btn-submit');
    await submitBtn.click();
    const reply = await createReply;
    await assertOk(reply, 'Character creation from the builder');
    const created = (await reply.json()) as { id?: string };
    world.characterId = requireValue(created.id, 'The character reply has no id.');

    await expect(modal.locator('.modal-dialog')).not.toBeVisible({ timeout: 10_000 });
  }
);

Then(
  'a new character card appears in the roster',
  async ({ page, world }) => {
    const name = requireValue(world.get<string>('characterName'), 'No character name. Fill in the builder first.');
    const card = createdCharacterCard(page, world);

    await expect(card).toBeVisible({ timeout: 10_000 });
    await expect(card).toContainText(name);
  }
);

When(
  '{word} clicks "Inspect Sheet"',
  async ({ page, world }, _persona: string) => {
    const inspectBtn = createdCharacterCard(page, world).getByRole('button', { name: 'Inspect Sheet', exact: true });

    await expect(inspectBtn).toBeVisible({ timeout: 10_000 });
    await inspectBtn.click();
  }
);

Then(
  'the browser navigates to {string} displaying {string}',
  async ({ page, world }, _pathPattern: string, expectedName: string) => {
    await expect
      .poll(() => page.evaluate(() => window.location.hash), { timeout: 10_000 })
      .toMatch(/^#\/characters\/.+/);

    const hash = await page.evaluate(() => window.location.hash);
    const id = hash.replace(/^#\/characters\//, '').split('?')[0];
    expect(id, 'The sheet route must name the character that this scenario created').toBe(world.characterId);

    const heading = page.locator(`${SHEET} .char-identity h1`);

    await expect(heading).toContainText(expectedName, { timeout: 10_000 });
  }
);

When(
  '{word} clicks the "-5 HP" adjustment button',
  async ({ page, world, auth, frontdoorApi }, _persona: string) => {
    const charId = await ensureOnCharacterSheet(page, world, auth, frontdoorApi);

    // Read the starting HP from the public character record. The Then step asserts the change from it.
    const token = requireValue(world.currentUser?.token, 'No access token. Sign the player in first.');
    const before = await frontdoorApi.getCharacter(charId, token);
    world.set('hpBefore', requireValue<number>(before.current_hp, 'The character record has no current_hp.'));

    const minus5Btn = page.locator(`${SHEET} button.hp-btn-minus-5`);

    await expect(minus5Btn).toBeVisible({ timeout: 10_000 });
    await minus5Btn.click();
  }
);

Then(
  'current HP updates from {int} to {int} and health bar recalculates',
  async ({ page, world, frontdoorApi }, fromHp: number, toHp: number) => {
    const hpBefore = requireValue(world.get<number>('hpBefore'), 'No starting HP. Run the HP adjustment step first.');
    expect(hpBefore, 'The public character record must hold the starting HP').toBe(fromHp);

    await expect(hitPointsValue(page)).toHaveText(currentHpText(toHp), { timeout: 10_000 });

    const charId = requireValue(world.characterId, 'No character id.');
    const token = requireValue(world.currentUser?.token, 'No access token.');
    await expect
      .poll(async () => (await frontdoorApi.getCharacter(charId, token)).current_hp, { timeout: 10_000 })
      .toBe(toHp);

    // The Hit Points card has one bar.
    await expect(page.locator(`${SHEET} .hp-bar-inner`)).toBeVisible({ timeout: 10_000 });
  }
);

When(
  '{word} refreshes the browser page',
  async ({ page }, _persona: string) => {
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForSelector('runefoble-character-sheet', { timeout: 10_000 });
  }
);

Then(
  'current HP remains {int}',
  async ({ page }, expectedHp: number) => {
    await expect(hitPointsValue(page)).toHaveText(currentHpText(expectedHp), { timeout: 10_000 });
  }
);

Given(
  '{word} has {string} in his inventory',
  async ({ page, world, auth, frontdoorApi, request }, _persona: string, itemName: string) => {
    const charId = await ensureOnCharacterSheet(page, world, auth, frontdoorApi);
    const token = requireValue(world.currentUser?.token, 'No access token. Sign the player in first.');

    // Setup goes through the public inventory route (ADR-0014). No backdoor seed.
    const itemId = itemName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    const res = await request.post(`${API_BASE_URL}/api/v1/characters/${charId}/inventory`, {
      headers: { 'Content-Type': 'application/json', ...bearerHeader(token) },
      data: { itemId, name: itemName, quantity: 1, weightLbs: 3 },
    });
    await assertOk(res, `Adding "${itemName}" to the inventory`);

    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForSelector(SHEET, { timeout: 15_000 });
  }
);

When(
  '{word} clicks "Equip" on {string} in his inventory table',
  async ({ page, world, auth, frontdoorApi }, _persona: string, itemName: string) => {
    await ensureOnCharacterSheet(page, world, auth, frontdoorApi);

    // This step runs on a fresh character, so Main Hand starts empty.
    // The web-first assertion fails the scenario if a prior step filled it.
    await expect(mainHandSlot(page).locator('button.unequip-btn')).toHaveCount(0, { timeout: 10_000 });

    const row = page
      .locator(`${SHEET} table.inventory-table tr.inventory-row`)
      .filter({ hasText: itemName });

    await expect(row).toBeVisible({ timeout: 15_000 });
    await row.locator('button.equip-btn').click();

    // Clicking Equip always opens the slot selector dialog.
    const dialog = page.locator(`${SHEET} .equip-dialog`);
    await expect(dialog).toBeVisible({ timeout: 10_000 });
    await dialog.locator('button.confirm-equip-btn').click();
  }
);

Then(
  '{string} appears in the Main Hand equipment slot',
  async ({ page }, itemName: string) => {
    const slot = mainHandSlot(page);

    await expect(slot).toBeVisible({ timeout: 10_000 });
    await expect(slot.locator('.slot-content')).toContainText(itemName, { timeout: 10_000 });
  }
);

Then(
  'inventory encumbrance updates',
  async ({ page }) => {
    const encBox = page.locator(`${SHEET} .encumbrance-box`);
    await expect(encBox).toBeVisible({ timeout: 10_000 });
    await expect(encBox.locator('.encumbrance-header')).toContainText(/Encumbrance/i, { timeout: 10_000 });
  }
);

When(
  '{word} clicks "Unequip"',
  async ({ page }, _persona: string) => {
    const unequipBtn = mainHandSlot(page).locator('button.unequip-btn');

    await expect(unequipBtn).toBeVisible({ timeout: 10_000 });
    await unequipBtn.click();
  }
);

Then(
  'the Main Hand slot becomes empty',
  async ({ page }) => {
    const slot = mainHandSlot(page);

    await expect(slot.locator('.slot-content')).toContainText(/Empty/i, { timeout: 10_000 });
    await expect(slot.locator('.slot-content')).not.toContainText('Longsword +1');
  }
);

When(
  '{word} sets the stand-in risk threshold to {string} and checks {string}',
  async ({ page, world, auth, frontdoorApi }, _persona: string, riskLevel: string, toggleLabel: string) => {
    await ensureOnCharacterSheet(page, world, auth, frontdoorApi);

    const guardrails = page.locator('runefoble-stand-in-guardrails');
    await expect(guardrails).toBeVisible({ timeout: 10_000 });

    await guardrails.getByRole('combobox', { name: 'Risk Appetite' }).selectOption(riskLevel);

    // The toggle must carry exactly the label in the feature text. No other checkbox stands in for it.
    const toggle = guardrails.getByRole('checkbox', { name: toggleLabel, exact: true });
    await expect(toggle).toHaveCount(1, { timeout: 10_000 });
    await toggle.setChecked(true);
  }
);

When(
  'clicks "Save Guardrails"',
  async ({ page }) => {
    const saveBtn = page
      .locator('runefoble-stand-in-guardrails')
      .getByRole('button', { name: 'Save Tactical Guardrails', exact: true });

    await expect(saveBtn).toBeVisible({ timeout: 10_000 });
    await saveBtn.click();
  }
);

Then(
  'a toast {string} appears',
  async ({ page }, toastMessage: string) => {
    // The App Shell toast appears only after the guardrails reach the character service.
    const toast = page.locator('.toast-notification').filter({ hasText: toastMessage });

    await expect(toast).toBeVisible({ timeout: 10_000 });
  }
);

Then(
  'reloading the page retains the {string} stance',
  async ({ page }, expectedStance: string) => {
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForSelector('runefoble-stand-in-guardrails', { timeout: 10_000 });

    const riskSelect = page
      .locator('runefoble-stand-in-guardrails')
      .getByRole('combobox', { name: 'Risk Appetite' });
    await expect(riskSelect).toHaveValue(expectedStance, { timeout: 10_000 });
  }
);
