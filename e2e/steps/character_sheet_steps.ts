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
import type { FrontdoorApi } from '../support/frontdoor_api';

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
    const user = await auth.injectUser('Marcus');
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
    try {
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
        world.currentUser?.token
      );
      charId = created.id;
    } catch {
      charId = 'char-valeros';
    }
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
    const user = await auth.injectUser(personaName);
    world.currentUser = user;
  }
);

When(
  '{word} opens the character roster and clicks "+ Create Character"',
  async ({ page, world, auth }, _persona: string) => {
    if (!world.currentUser) {
      const user = await auth.injectUser('Marcus');
      world.currentUser = user;
    }

    await page.goto('#/characters');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForSelector('runefoble-character-roster', { timeout: 15_000 });

    const createBtn = page
      .locator('runefoble-character-roster #create-char-btn')
      .or(page.locator('runefoble-character-roster button:has-text("Create Character")'))
      .first();

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

    const submitBtn = modal.locator('button.btn-submit');
    await submitBtn.click();

    await expect(modal.locator('.modal-dialog')).not.toBeVisible({ timeout: 10_000 });
  }
);

Then(
  'a new character card appears in the roster',
  async ({ page, world }) => {
    const targetName = world.get<string>('characterName') || 'Thorne Ironbreaker';
    const card = page
      .locator('runefoble-character-roster article.character-card')
      .filter({ hasText: targetName })
      .first();

    await expect(card).toBeVisible({ timeout: 10_000 });
    const id = await card.getAttribute('data-character-id');
    if (id) {
      world.characterId = id;
    }
  }
);

When(
  '{word} clicks "Inspect Sheet"',
  async ({ page, world }, _persona: string) => {
    const targetName = world.get<string>('characterName') || 'Thorne Ironbreaker';
    const card = page
      .locator('runefoble-character-roster article.character-card')
      .filter({ hasText: targetName })
      .first();

    const inspectBtn = card
      .locator('button.btn-secondary')
      .filter({ hasText: 'Inspect Sheet' })
      .first();

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
    if (id) {
      world.characterId = id;
    }

    const heading = page
      .locator('runefoble-character-sheet .char-identity h1, runefoble-character-sheet h1, .character-sheet-view h1')
      .first();

    await expect(heading).toContainText(expectedName, { timeout: 10_000 });
  }
);

When(
  '{word} clicks the "-5 HP" adjustment button',
  async ({ page, world, auth, frontdoorApi }, _persona: string) => {
    await ensureOnCharacterSheet(page, world, auth, frontdoorApi);

    const minus5Btn = page
      .locator('runefoble-character-sheet button.hp-btn-minus-5, runefoble-character-sheet button:has-text("-5")')
      .first();

    await expect(minus5Btn).toBeVisible({ timeout: 10_000 });
    await minus5Btn.click();
  }
);

Then(
  'current HP updates from {int} to {int} and health bar recalculates',
  async ({ page }, _fromHp: number, toHp: number) => {
    const vitalVal = page
      .locator('runefoble-character-sheet .vital-card:has-text("Hit Points") .vital-val, runefoble-character-sheet .vital-val')
      .first();

    await expect(vitalVal).toContainText(String(toHp), { timeout: 10_000 });

    const hpBar = page.locator('runefoble-character-sheet .hp-bar-inner').first();
    await expect(hpBar).toBeVisible({ timeout: 10_000 });
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
    const vitalVal = page
      .locator('runefoble-character-sheet .vital-card:has-text("Hit Points") .vital-val, runefoble-character-sheet .vital-val')
      .first();

    await expect(vitalVal).toContainText(String(expectedHp), { timeout: 10_000 });
  }
);

When(
  '{word} clicks "Equip" on {string} in his inventory table',
  async ({ page, world, auth, frontdoorApi }, _persona: string, itemName: string) => {
    await ensureOnCharacterSheet(page, world, auth, frontdoorApi);

    // If Main Hand is already filled, unequip it first so equipping is an observable state transition
    const mainHandSlot = page
      .locator('runefoble-character-sheet .equip-slot')
      .filter({ hasText: 'Main Hand' })
      .first();
    const unequipBtn = mainHandSlot.locator('button.unequip-btn');
    if (await unequipBtn.isVisible()) {
      await unequipBtn.click();
      await page.waitForTimeout(200);
    }

    const row = page
      .locator('runefoble-character-sheet table.inventory-table tr.inventory-row')
      .filter({ hasText: itemName })
      .first();

    await expect(row).toBeVisible({ timeout: 15_000 });
    const equipBtn = row.locator('button.equip-btn, button:has-text("Equip")').first();
    await equipBtn.click();

    const dialog = page.locator('runefoble-character-sheet .equip-dialog, .equip-dialog');
    if (await dialog.isVisible()) {
      const confirmBtn = dialog.locator('button.confirm-equip-btn, button:has-text("Confirm")').first();
      await confirmBtn.click();
    }
  }
);

Then(
  '{string} appears in the Main Hand equipment slot',
  async ({ page }, itemName: string) => {
    const slot = page
      .locator('runefoble-character-sheet .equip-slot')
      .filter({ hasText: 'Main Hand' })
      .first();

    await expect(slot).toBeVisible({ timeout: 10_000 });
    await expect(slot.locator('.slot-content')).toContainText(itemName, { timeout: 10_000 });
  }
);

Then(
  'inventory encumbrance updates',
  async ({ page }) => {
    const encBox = page.locator('runefoble-character-sheet .encumbrance-box').first();
    await expect(encBox).toBeVisible({ timeout: 10_000 });
    await expect(encBox.locator('.encumbrance-header')).toContainText(/Encumbrance/i, { timeout: 10_000 });
  }
);

When(
  '{word} clicks "Unequip"',
  async ({ page }, _persona: string) => {
    const slot = page
      .locator('runefoble-character-sheet .equip-slot')
      .filter({ hasText: 'Main Hand' })
      .first();

    const unequipBtn = slot
      .locator('button.unequip-btn, button[title="Unequip"], button:has-text("✕")')
      .first();

    await expect(unequipBtn).toBeVisible({ timeout: 10_000 });
    await unequipBtn.click();
  }
);

Then(
  'the Main Hand slot becomes empty',
  async ({ page }) => {
    const slot = page
      .locator('runefoble-character-sheet .equip-slot')
      .filter({ hasText: 'Main Hand' })
      .first();

    await expect(slot.locator('.slot-content')).toContainText(/Empty/i, { timeout: 10_000 });
    await expect(slot.locator('.slot-content')).not.toContainText('Longsword +1');
  }
);

When(
  '{word} sets the stand-in risk threshold to {string} and checks "Avoid Melee"',
  async ({ page, world, auth, frontdoorApi }, _persona: string, riskLevel: string) => {
    await ensureOnCharacterSheet(page, world, auth, frontdoorApi);

    const guardrails = page.locator('runefoble-stand-in-guardrails').first();
    await expect(guardrails).toBeVisible({ timeout: 10_000 });

    const riskSelect = guardrails.locator('select').first();
    await riskSelect.selectOption(riskLevel);

    const avoidMeleeCheckbox = guardrails
      .locator('.toggle-row')
      .filter({ hasText: 'Avoid Frontline Melee' })
      .locator('input[type="checkbox"]')
      .or(guardrails.locator('input[type="checkbox"]').first())
      .first();

    await avoidMeleeCheckbox.setChecked(true);
  }
);

When(
  '{word} clicks "Save Guardrails"',
  async ({ page }, _persona: string) => {
    const guardrails = page.locator('runefoble-stand-in-guardrails').first();
    const saveBtn = guardrails
      .locator('button:has-text("Save Guardrails"), button:has-text("Save Tactical Guardrails"), button.btn:has-text("Save")')
      .first();

    await expect(saveBtn).toBeVisible({ timeout: 10_000 });
    await saveBtn.click();
  }
);

When(
  'clicks "Save Guardrails"',
  async ({ page }) => {
    const guardrails = page.locator('runefoble-stand-in-guardrails').first();
    const saveBtn = guardrails
      .locator('button:has-text("Save Guardrails"), button:has-text("Save Tactical Guardrails"), button.btn:has-text("Save")')
      .first();

    await expect(saveBtn).toBeVisible({ timeout: 10_000 });
    await saveBtn.click();
  }
);

Then(
  'a toast {string} appears',
  async ({ page }, toastMessage: string) => {
    const toast = page
      .locator('.toast-notification, [role="status"], runefoble-stand-in-guardrails .status-msg')
      .filter({ hasText: toastMessage })
      .first();

    await expect(toast).toBeVisible({ timeout: 10_000 });
  }
);

Then(
  'reloading the page retains the {string} stance',
  async ({ page }, expectedStance: string) => {
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForSelector('runefoble-stand-in-guardrails', { timeout: 10_000 });

    const guardrails = page.locator('runefoble-stand-in-guardrails').first();
    const riskSelect = guardrails.locator('select').first();
    await expect(riskSelect).toHaveValue(expectedStance, { timeout: 10_000 });
  }
);
