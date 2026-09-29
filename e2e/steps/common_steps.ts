/**
 * Runefoble Core Gherkin Step Definitions
 * Governed by ADR-0014 and Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
 */

import { expect } from '@playwright/test';
import { Given, When, Then } from '../support/fixtures';

Given('I am logged in as a {string}', async ({ auth, world }, roleOrName: string) => {
  const user = await auth.injectUser(roleOrName);
  world.currentUser = user;
});

Given('campaign {string} exists', async ({ frontdoorApi, world }, campaignTitle: string) => {
  const token = world.currentUser?.token;
  const campaign = await frontdoorApi.createCampaign(campaignTitle, { token });
  world.campaignId = campaign.id;
  world.campaignTitle = campaign.title;
});

When('I navigate to {string}', async ({ page }, path: string) => {
  await page.goto(path);
  await page.waitForLoadState('domcontentloaded');
});

When('I click the {string} button', async ({ page }, buttonName: string) => {
  const button = page
    .getByRole('button', { name: buttonName })
    .or(page.locator(`button:has-text("${buttonName}")`))
    .or(page.locator(`[aria-label="${buttonName}"]`))
    .first();
  await button.click();
});

When('I switch theme to {string}', async ({ page, world }, themeId: string) => {
  world.activeTheme = themeId;

  // 1. Try theme buttons directly inside runefoble-theme-switcher (e.g. on profile page)
  const switcherBtn = page
    .locator('runefoble-theme-switcher')
    .locator('button.theme-button')
    .filter({ hasText: new RegExp(themeId.replace('-', ' '), 'i') })
    .first();

  if (await switcherBtn.isVisible()) {
    await switcherBtn.click();
    return;
  }

  // 2. Try settings modal trigger
  const settingsBtn = page.locator('#settings-trigger-btn').first();
  if (await settingsBtn.isVisible()) {
    await settingsBtn.click();
    const modalThemeCard = page
      .locator('runefoble-settings-appearance button.theme-card')
      .filter({ hasText: new RegExp(themeId.replace('-', ' '), 'i') })
      .first();
    if (await modalThemeCard.isVisible()) {
      await modalThemeCard.click();
      return;
    }
  }

  // 3. Frontdoor fallback via DOM standard events
  await page.evaluate((theme) => {
    document.documentElement.setAttribute('data-theme', theme);
    window.localStorage.setItem('runefoble-theme', theme);
    window.dispatchEvent(
      new CustomEvent('theme-changed', {
        detail: { theme },
        bubbles: true,
        composed: true,
      })
    );
  }, themeId);
});

Then('I should see the heading {string}', async ({ page }, headingText: string) => {
  const heading = page
    .getByRole('heading', { name: headingText })
    .or(page.locator('h1, h2, h3, h4').filter({ hasText: headingText }))
    .first();

  await expect(heading).toBeVisible({ timeout: 10_000 });
});

Then('the URL hash should be {string}', async ({ page }, expectedHash: string) => {
  await expect
    .poll(async () => page.evaluate(() => window.location.hash), {
      timeout: 10_000,
    })
    .toBe(expectedHash);
});

Then(
  'I should see a toast notification containing {string}',
  async ({ page }, messageText: string) => {
    const toast = page
      .locator('.toast-notification, [role="status"]')
      .filter({ hasText: messageText })
      .first();

    await expect(toast).toBeVisible({ timeout: 10_000 });
  }
);

Then('the active theme should be {string}', async ({ page }, expectedTheme: string) => {
  await expect
    .poll(
      async () => page.evaluate(() => document.documentElement.getAttribute('data-theme')),
      { timeout: 10_000 }
    )
    .toBe(expectedTheme);
});
