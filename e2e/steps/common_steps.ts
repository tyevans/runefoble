/**
 * Runefoble Core Gherkin Step Definitions
 * Governed by ADR-0014 and Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
 */

import { expect } from '@playwright/test';
import { Given, When, Then } from '../support/fixtures';

Given('I am logged in as a {string}', async ({ auth, world }, roleOrName: string) => {
  const user = await auth.signInAs(roleOrName);
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
  // The accessible name must equal the feature text. Strict mode fails on zero or several matches.
  const button = page.getByRole('button', { name: buttonName, exact: true });
  await button.click();
});

When('I switch theme to {string}', async ({ page, world }, themeId: string) => {
  world.activeTheme = themeId;
  const label = new RegExp(themeId.replace('-', ' '), 'i');

  // 1. Theme buttons inside runefoble-theme-switcher (e.g. on the profile page)
  const switcherBtn = page
    .locator('runefoble-theme-switcher')
    .locator('button.theme-button')
    .filter({ hasText: label });

  if (await switcherBtn.isVisible()) {
    await switcherBtn.click();
    return;
  }

  // 2. Settings modal: open it, then pick the theme card
  const settingsBtn = page.locator('#settings-trigger-btn');
  await expect(settingsBtn, `No theme control visible for "${themeId}"`).toBeVisible({
    timeout: 10_000,
  });
  await settingsBtn.click();
  const modalThemeCard = page
    .locator('runefoble-settings-appearance button.theme-card')
    .filter({ hasText: label });
  await expect(modalThemeCard, `No theme card visible for "${themeId}"`).toBeVisible({
    timeout: 10_000,
  });
  await modalThemeCard.click();
});

Then('I should see the heading {string}', async ({ page }, headingText: string) => {
  const heading = page.getByRole('heading', { name: headingText, exact: true });

  await expect(heading).toBeVisible({ timeout: 10_000 });
});

Then('the URL hash should be {string}', async ({ page }, expectedHash: string) => {
  await expect
    .poll(async () => page.evaluate(() => window.location.hash), {
      timeout: 10_000,
    })
    .toBe(expectedHash);
});

Then('the active theme should be {string}', async ({ page }, expectedTheme: string) => {
  // Read the user-visible control state: the pressed switcher button, or the
  // active settings theme card. Setup never writes the theme attribute.
  const label = new RegExp(expectedTheme.replace('-', ' '), 'i');
  const switcherActive = page.locator('runefoble-theme-switcher button.theme-button[aria-pressed="true"]');
  const modalActive = page.locator('runefoble-settings-appearance button.theme-card.active');
  const active = (await switcherActive.isVisible()) ? switcherActive : modalActive;

  await expect(active, `No active theme control visible`).toBeVisible({ timeout: 10_000 });
  await expect(active).toContainText(label);
});
