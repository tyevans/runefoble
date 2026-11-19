/**
 * Runefoble Campaign Hub Lifecycle and Navigation Playwright BDD Step Definitions
 *
 * Automates end-to-end user journeys for campaign creation, SpiceDB Zanzibar member
 * role assignments, shareable invite token generation and clipboard copying, and
 * tab transitions without dead ends per ADR-0001, ADR-0004, ADR-0013, ADR-0014,
 * and Hard Invariant 7 (Blackbox Frontdoor TDD).
 */

import { expect, type Page } from '@playwright/test';
import { Given, When, Then } from '../support/fixtures';
import type { AuthFixtures } from '../support/auth_fixtures';
import type { FrontdoorApi } from '../support/frontdoor_api';
import type { World } from '../support/world';
import { requireValue } from '../support/guards';
import { findPersona, resolvePersonaKey } from '../support/personas';

/** The Zitadel user id of a persona named in the feature text, from the run's persona registry. */
function personaUserId(name: string): string {
  return findPersona(resolvePersonaKey(name)).userId;
}

/** The roster row of one member. The `data-user-id` attribute makes the match exact. */
function memberRow(page: Page, userId: string) {
  return page.locator(`runefoble-campaign-members .member-item[data-user-id="${userId}"]`);
}

function campaignTab(page: Page, tabName: string) {
  return page.locator('nav.campaign-nav-tabs').getByRole('tab', { name: tabName, exact: true });
}

async function ensureOnCampaignOverview(
  page: Page,
  world: World,
  auth: AuthFixtures,
  frontdoorApi: FrontdoorApi
): Promise<void> {
  const evelynUser = await auth.signInAs('evelyn', page);
  world.currentUser = evelynUser;
  world.setPage('evelyn', page);

  if (!world.campaignId) {
    // Setup goes through the public campaigns route. A failed call throws with the response body.
    const token = requireValue(world.currentUser?.token, 'No access token. Sign Evelyn in before campaign setup.');
    const camp = await frontdoorApi.createCampaign('Wrath of the Lich King', { setting: 'Northrend', token });
    world.campaignId = requireValue(camp.id, 'The campaign reply has no id.');
    world.campaignTitle = camp.title;
  }

  const campaignId = world.campaignId;
  const targetHash = `#/campaigns/${campaignId}`;
  const currentHash = await page.evaluate(() => window.location.hash);

  if (currentHash !== targetHash) {
    await page.goto(targetHash);
    await page.waitForLoadState('domcontentloaded');
  }

  const membersComp = page.locator('runefoble-campaign-members');
  await expect(membersComp).toBeVisible({ timeout: 15_000 });
}

Given('Evelyn is logged in as a Dungeon Master', async ({ auth, world, page }) => {
  const evelynUser = await auth.signInAs('evelyn', page);
  world.currentUser = evelynUser;
  world.setPage('evelyn', page);

  await page.goto('#/campaigns');
  await page.waitForLoadState('domcontentloaded');
  await expect(page.locator('runefoble-campaign-dashboard')).toBeVisible({ timeout: 15_000 });
});

When(
  'she clicks {string} and fills in title {string} and setting {string}',
  async ({ page, world }, buttonName: string, title: string, setting: string) => {
    world.campaignTitle = title;

    // The dashboard header holds the button. The empty state can show a second one.
    const newCampaignBtn = page
      .locator('runefoble-campaign-dashboard header.dashboard-header')
      .getByRole('button', { name: buttonName, exact: true });
    await expect(newCampaignBtn).toBeVisible({ timeout: 10_000 });
    await newCampaignBtn.click();

    const creator = page.locator('runefoble-campaign-creator');
    const modal = creator.locator('.modal-card');
    await expect(modal).toBeVisible({ timeout: 10_000 });

    const titleInput = creator.locator('#campaign-title');
    await titleInput.waitFor({ state: 'visible', timeout: 10_000 });
    await titleInput.fill(title);

    const settingInput = creator.locator('#campaign-setting');
    await settingInput.waitFor({ state: 'visible', timeout: 10_000 });
    await settingInput.fill(setting);

    const submitBtn = creator.getByRole('button', { name: 'Create Campaign', exact: true });
    await submitBtn.click();
  }
);

Then(
  'a new campaign should be created and navigation transitions to {string}',
  async ({ page, world }, _expectedRoutePattern: string) => {
    await expect
      .poll(async () => page.evaluate(() => window.location.hash), { timeout: 15_000 })
      .toMatch(/^#\/campaigns\/[^/]+$/);

    const currentHash = await page.evaluate(() => window.location.hash);
    const campaignId = currentHash.replace(/^#\/campaigns\//, '');
    world.campaignId = campaignId;
    expect(campaignId).toBeTruthy();

    await expect(page.locator('runefoble-campaign-header')).toBeVisible({ timeout: 15_000 });
    await expect(page.locator('runefoble-campaign-members')).toBeVisible({ timeout: 15_000 });
  }
);

Then(
  'she should be displayed in the Campaign Roster as {string}',
  async ({ page, world }, expectedRole: string) => {
    const owner = world.currentUser;
    if (!owner) throw new Error('No signed-in persona. Sign Evelyn in before the roster check.');
    const membersComp = page.locator('runefoble-campaign-members');
    await expect(membersComp).toBeVisible({ timeout: 15_000 });

    const ownerRow = memberRow(page, owner.userId);

    await expect(ownerRow).toBeVisible({ timeout: 10_000 });
    await expect(ownerRow).toContainText(owner.username);
    await expect(ownerRow.locator('.badge-role')).toHaveText(expectedRole);
  }
);

Given(
  'a campaign exists with members {string} and {string}',
  async ({ auth, world, page, frontdoorApi }, member1: string, member2: string) => {
    const evelynUser = await auth.signInAs('evelyn', page);
    world.currentUser = evelynUser;
    world.setPage('evelyn', page);

    const token = requireValue(world.currentUser.token, 'No access token. Sign Evelyn in before campaign setup.');
    if (!world.campaignId) {
      const camp = await frontdoorApi.createCampaign('Wrath of the Lich King', { setting: 'Northrend', token });
      world.campaignId = requireValue(camp.id, 'The campaign reply has no id.');
      world.campaignTitle = camp.title;
    }

    const campaignId = world.campaignId;
    const member1Id = personaUserId(member1);
    const member2Id = personaUserId(member2);

    // Role setup goes through the public roles route with the personas' real user ids. A failure stops the step.
    await frontdoorApi.assignCampaignRole(campaignId, member1Id, 'player', token);
    await frontdoorApi.assignCampaignRole(campaignId, member2Id, 'player', token);

    await page.goto(`#/campaigns/${campaignId}`);
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('runefoble-campaign-members')).toBeVisible({ timeout: 15_000 });

    // The API roster must list both members. The UI must render them.
    const members = await frontdoorApi.listCampaignMembers(campaignId, token);
    const memberIds = members.map((m: { user_id: string }) => m.user_id);
    expect(memberIds).toContain(member1Id);
    expect(memberIds).toContain(member2Id);

    await expect(memberRow(page, member1Id)).toBeVisible({ timeout: 10_000 });
    await expect(memberRow(page, member2Id)).toBeVisible({ timeout: 10_000 });
  }
);

When(
  "Evelyn changes Marcus's role from {string} to {string}",
  async ({ page }, _fromRole: string, toRole: string) => {
    const marcusRow = memberRow(page, personaUserId('Marcus'));
    await expect(marcusRow).toBeVisible({ timeout: 10_000 });

    const roleSelect = marcusRow.locator('.role-select');
    await roleSelect.waitFor({ state: 'visible', timeout: 10_000 });

    const roleValue =
      toRole.toLowerCase().includes('master') || toRole.toLowerCase().includes('dm')
        ? 'dungeon_master'
        : toRole.toLowerCase();

    await roleSelect.selectOption({ value: roleValue });
  }
);

Then('a toast notification {string} appears', async ({ page }, messageText: string) => {
  // The App Shell renders one toast at a time.
  const toast = page.locator('.toast-notification').filter({ hasText: messageText });
  await expect(toast).toBeVisible({ timeout: 10_000 });
});

Then("Marcus's role dropdown shows {string}", async ({ page }, expectedRoleText: string) => {
  const marcusRow = memberRow(page, personaUserId('Marcus'));
  await expect(marcusRow).toBeVisible({ timeout: 10_000 });

  const roleSelect = marcusRow.locator('.role-select');
  const expectedValue =
    expectedRoleText.toLowerCase().includes('master') ||
    expectedRoleText.toLowerCase().includes('dm')
      ? 'dungeon_master'
      : expectedRoleText.toLowerCase();

  await expect(roleSelect).toHaveValue(expectedValue, { timeout: 10_000 });
});

When(
  'Evelyn clicks {string}, selects role {string}, and clicks {string}',
  async (
    { auth, page, world, frontdoorApi },
    inviteBtnName: string,
    roleName: string,
    generateBtnName: string
  ) => {
    await ensureOnCampaignOverview(page, world, auth, frontdoorApi);

    const inviteBtn = page
      .locator('runefoble-campaign-members header.members-header')
      .getByRole('button', { name: inviteBtnName, exact: true });
    await expect(inviteBtn).toBeVisible({ timeout: 10_000 });
    await inviteBtn.click();

    const modal = page.locator('runefoble-campaign-members .modal-card');
    await expect(modal).toBeVisible({ timeout: 10_000 });

    const roleSelect = modal.locator('#invite-role-select');
    const targetValue = roleName.toLowerCase().includes('spectator') ? 'spectator' : 'player';
    await roleSelect.selectOption({ value: targetValue });

    const generateBtn = modal.getByRole('button', { name: generateBtnName, exact: true });
    await expect(generateBtn).toBeVisible({ timeout: 10_000 });
    await generateBtn.click();
  }
);

Then('a shareable invite link containing a signed token is displayed', async ({ page }) => {
  const linkInput = page.locator('runefoble-campaign-members .invite-link-input');
  await expect(linkInput).toBeVisible({ timeout: 10_000 });

  await expect
    .poll(async () => linkInput.inputValue(), { timeout: 10_000 })
    .toMatch(/\/join\/[a-zA-Z0-9_\-]+/);
});

Then(
  'clicking {string} copies the valid join URL to the clipboard',
  async ({ page }, copyBtnName: string) => {
    // playwright.config.ts grants clipboard access to each browser project. A failed read fails the step.
    const modal = page.locator('runefoble-campaign-members .modal-card');
    const copyBtn = modal.getByRole('button', { name: copyBtnName, exact: true });
    await expect(copyBtn).toBeVisible({ timeout: 10_000 });
    await copyBtn.click();

    await expect(modal.locator('.copied-badge')).toBeVisible({ timeout: 10_000 });

    const inputVal = await modal.locator('.invite-link-input').inputValue();
    expect(inputVal).toMatch(/\/join\/.+/);

    const clipboardText = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboardText).toBe(inputVal);
  }
);

When(
  'Evelyn clicks {string}, the URL hash becomes {string}',
  async ({ auth, page, world, frontdoorApi }, tabName: string, expectedHashPattern: string) => {
    await ensureOnCampaignOverview(page, world, auth, frontdoorApi);

    const tab = campaignTab(page, tabName);
    await expect(tab).toBeVisible({ timeout: 10_000 });
    await tab.click();

    const expectedSuffix = expectedHashPattern.replace(/^#\/campaigns\/:id/, '');
    const expectedRegex = new RegExp(`^#/campaigns/[^/]+${expectedSuffix}$`);

    await expect
      .poll(async () => page.evaluate(() => window.location.hash), { timeout: 10_000 })
      .toMatch(expectedRegex);

    if (tabName.toLowerCase().includes('character')) {
      await expect(page.locator('runefoble-character-roster')).toBeVisible({ timeout: 10_000 });
    }
  }
);

When(
  'Evelyn clicks {string}, the URL hash becomes {string} and <runefoble-campaign-atlas> renders',
  async ({ page, world }, tabName: string, expectedHashPattern: string) => {
    const tab = campaignTab(page, tabName);
    await expect(tab).toBeVisible({ timeout: 10_000 });
    await tab.click();

    const expectedSuffix = expectedHashPattern.replace(/^#\/campaigns\/:id/, '');
    const expectedRegex = new RegExp(`^#/campaigns/[^/]+${expectedSuffix}$`);

    await expect
      .poll(async () => page.evaluate(() => window.location.hash), { timeout: 10_000 })
      .toMatch(expectedRegex);

    const atlas = page.locator('runefoble-campaign-atlas');
    await expect(atlas).toBeVisible({ timeout: 10_000 });
  }
);

When(
  'Evelyn clicks {string}, the URL hash becomes {string} and <runefoble-campaign-analytics> renders',
  async ({ page, world }, tabName: string, expectedHashPattern: string) => {
    const tab = campaignTab(page, tabName);
    await expect(tab).toBeVisible({ timeout: 10_000 });
    await tab.click();

    const expectedSuffix = expectedHashPattern.replace(/^#\/campaigns\/:id/, '');
    const expectedRegex = new RegExp(`^#/campaigns/[^/]+${expectedSuffix}$`);

    await expect
      .poll(async () => page.evaluate(() => window.location.hash), { timeout: 10_000 })
      .toMatch(expectedRegex);

    const analytics = page.locator('runefoble-campaign-analytics');
    await expect(analytics).toBeVisible({ timeout: 10_000 });
  }
);

When(
  'Evelyn clicks {string}, the URL hash returns to {string}',
  async ({ page, world }, tabName: string, _expectedHashPattern: string) => {
    const tab = campaignTab(page, tabName);
    await expect(tab).toBeVisible({ timeout: 10_000 });
    await tab.click();

    await expect
      .poll(async () => page.evaluate(() => window.location.hash), { timeout: 10_000 })
      .toMatch(/^#\/campaigns\/[^/]+$/);

    await expect(page.locator('runefoble-campaign-members')).toBeVisible({ timeout: 10_000 });
  }
);
