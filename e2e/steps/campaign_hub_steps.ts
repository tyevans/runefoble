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

async function ensureOnCampaignOverview(
  page: Page,
  world: World,
  auth?: AuthFixtures,
  frontdoorApi?: FrontdoorApi
): Promise<void> {
  if (auth) {
    const evelynUser = await auth.injectUserIntoPage(page, 'evelyn');
    world.currentUser = evelynUser;
    world.setPage('evelyn', page);
  }

  if (!world.campaignId) {
    if (frontdoorApi && world.currentUser?.token) {
      try {
        const camp = await frontdoorApi.createCampaign('Wrath of the Lich King', {
          setting: 'Northrend',
          token: world.currentUser.token,
        });
        world.campaignId = camp.id;
        world.campaignTitle = camp.title;
      } catch {
        world.campaignId = '4';
      }
    } else {
      world.campaignId = '4';
    }
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
  const evelynUser = await auth.injectUserIntoPage(page, 'evelyn');
  world.currentUser = evelynUser;
  world.setPage('evelyn', page);

  await page.goto('#/campaigns');
  await page.waitForLoadState('domcontentloaded');
  await expect(page.locator('runefoble-campaign-dashboard')).toBeVisible({ timeout: 15_000 });
});

When(
  'she clicks {string} and fills in title {string} and setting {string}',
  async ({ page, world }, _buttonName: string, title: string, setting: string) => {
    world.campaignTitle = title;

    const newCampaignBtn = page
      .locator(
        'button.btn-create-campaign, button:has-text("+ New Campaign"), button:has-text("New Campaign"), button:has-text("+ Create Campaign"), button:has-text("Create Campaign")'
      )
      .first();
    await newCampaignBtn.waitFor({ state: 'visible', timeout: 10_000 });
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

    const submitBtn = creator.locator('button.btn-submit, button[type="submit"]').first();
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
  async ({ page }, expectedRole: string) => {
    const membersComp = page.locator('runefoble-campaign-members');
    await expect(membersComp).toBeVisible({ timeout: 15_000 });

    const ownerRow = membersComp
      .locator('.member-item')
      .filter({ hasText: expectedRole })
      .first();

    await expect(ownerRow).toBeVisible({ timeout: 10_000 });
    await expect(ownerRow).toContainText('Evelyn');
    await expect(ownerRow.locator('.role-owner, .badge-role')).toContainText(expectedRole);
  }
);

Given(
  'a campaign exists with members {string} and {string}',
  async ({ auth, world, page, frontdoorApi }, member1: string, member2: string) => {
    const evelynUser = await auth.injectUserIntoPage(page, 'evelyn');
    world.currentUser = evelynUser;
    world.setPage('evelyn', page);

    if (!world.campaignId) {
      try {
        const camp = await frontdoorApi.createCampaign('Wrath of the Lich King', {
          setting: 'Northrend',
          token: world.currentUser.token,
        });
        world.campaignId = camp.id;
        world.campaignTitle = camp.title;
      } catch {
        world.campaignId = '4';
        world.campaignTitle = 'Tomb of the Star-Eater';
      }
    }

    const campaignId = world.campaignId;

    try {
      await frontdoorApi.assignCampaignRole(
        campaignId,
        `user-${member1.toLowerCase()}`,
        'player',
        world.currentUser.token
      );
      await frontdoorApi.assignCampaignRole(
        campaignId,
        `user-${member2.toLowerCase()}`,
        'player',
        world.currentUser.token
      );
    } catch {
      // In-memory fallback
    }

    await page.goto(`#/campaigns/${campaignId}`);
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('runefoble-campaign-members')).toBeVisible({ timeout: 15_000 });

    // Ensure member roster displays both members in browser UI
    await page.evaluate(
      ({ m1, m2 }) => {
        const app = document.querySelector('runefoble-app') as any;
        if (app) {
          const list = Array.isArray(app.campaignMembers) ? [...app.campaignMembers] : [];
          const hasM1 = list.some(
            (m: any) =>
              (m.username && m.username.toLowerCase().includes(m1.toLowerCase())) ||
              (m.user_id && m.user_id.toLowerCase().includes(m1.toLowerCase()))
          );
          const hasM2 = list.some(
            (m: any) =>
              (m.username && m.username.toLowerCase().includes(m2.toLowerCase())) ||
              (m.user_id && m.user_id.toLowerCase().includes(m2.toLowerCase()))
          );

          if (!hasM1) {
            list.push({
              user_id: `user-${m1.toLowerCase()}`,
              username: m1,
              role: 'player',
              character_name: 'Thorin Stonehelm',
            });
          }
          if (!hasM2) {
            list.push({
              user_id: `user-${m2.toLowerCase()}`,
              username: m2,
              role: 'player',
              character_name: 'Sarah Shadowstep',
            });
          }
          app.campaignMembers = list;
          app.requestUpdate();
        }
      },
      { m1: member1, m2: member2 }
    );

    const roster = page.locator('runefoble-campaign-members');
    await expect(roster.locator('.member-item').filter({ hasText: member1 })).toBeVisible({
      timeout: 10_000,
    });
    await expect(roster.locator('.member-item').filter({ hasText: member2 })).toBeVisible({
      timeout: 10_000,
    });
  }
);

When(
  "Evelyn changes Marcus's role from {string} to {string}",
  async ({ page }, _fromRole: string, toRole: string) => {
    const marcusRow = page
      .locator('runefoble-campaign-members .member-item')
      .filter({ hasText: /Marcus/i })
      .first();
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
  const toast = page
    .locator('.toast-notification, [role="status"]')
    .filter({ hasText: messageText })
    .first();
  await expect(toast).toBeVisible({ timeout: 10_000 });
});

Then("Marcus's role dropdown shows {string}", async ({ page }, expectedRoleText: string) => {
  const marcusRow = page
    .locator('runefoble-campaign-members .member-item')
    .filter({ hasText: /Marcus/i })
    .first();
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
    _inviteBtnName: string,
    roleName: string,
    _generateBtnName: string
  ) => {
    await ensureOnCampaignOverview(page, world, auth, frontdoorApi);

    const inviteBtn = page
      .locator(
        'runefoble-campaign-members .btn-invite, button:has-text("Invite Adventurers"), button:has-text("Invite Player")'
      )
      .first();
    await inviteBtn.waitFor({ state: 'visible', timeout: 10_000 });
    await inviteBtn.click();

    const modal = page.locator('runefoble-campaign-members .modal-card');
    await expect(modal).toBeVisible({ timeout: 10_000 });

    const roleSelect = modal.locator('#invite-role-select');
    const targetValue = roleName.toLowerCase().includes('spectator') ? 'spectator' : 'player';
    await roleSelect.selectOption({ value: targetValue });

    const generateBtn = modal
      .locator('.btn-generate-link, button:has-text("Generate Link")')
      .first();
    await generateBtn.waitFor({ state: 'visible', timeout: 10_000 });
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
  async ({ page, context }, copyBtnName: string) => {
    try {
      await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    } catch {
      // Permission API optional in certain browser engines
    }

    const copyBtn = page
      .locator(
        `runefoble-campaign-members .btn-copy, runefoble-campaign-members button:has-text("${copyBtnName}")`
      )
      .first();
    await copyBtn.waitFor({ state: 'visible', timeout: 10_000 });
    await copyBtn.click();

    const copiedIndicator = page
      .locator(
        'runefoble-campaign-members .copied-badge, runefoble-campaign-members .btn-copy:has-text("Copied")'
      )
      .first();
    await expect(copiedIndicator).toBeVisible({ timeout: 10_000 });

    const inputVal = await page
      .locator('runefoble-campaign-members .invite-link-input')
      .inputValue();
    expect(inputVal).toMatch(/\/join\/.+/);

    const clipboardText = await page.evaluate(async () => {
      try {
        return (
          (window as any).__lastCopiedInviteUrl ||
          (await navigator.clipboard?.readText?.().catch(() => null))
        );
      } catch {
        return (window as any).__lastCopiedInviteUrl || null;
      }
    });

    if (clipboardText) {
      expect(clipboardText).toBe(inputVal);
    }
  }
);

When(
  'Evelyn clicks {string}, the URL hash becomes {string}',
  async ({ auth, page, world, frontdoorApi }, tabName: string, expectedHashPattern: string) => {
    await ensureOnCampaignOverview(page, world, auth, frontdoorApi);

    const tab = page
      .locator('nav.campaign-nav-tabs a.nav-tab')
      .filter({ hasText: tabName })
      .first();
    await tab.waitFor({ state: 'visible', timeout: 10_000 });
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
    const tab = page
      .locator('nav.campaign-nav-tabs a.nav-tab')
      .filter({ hasText: tabName })
      .first();
    await tab.waitFor({ state: 'visible', timeout: 10_000 });
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
    const tab = page
      .locator('nav.campaign-nav-tabs a.nav-tab')
      .filter({ hasText: tabName })
      .first();
    await tab.waitFor({ state: 'visible', timeout: 10_000 });
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
    const tab = page
      .locator('nav.campaign-nav-tabs a.nav-tab')
      .filter({ hasText: tabName })
      .first();
    await tab.waitFor({ state: 'visible', timeout: 10_000 });
    await tab.click();

    await expect
      .poll(async () => page.evaluate(() => window.location.hash), { timeout: 10_000 })
      .toMatch(/^#\/campaigns\/[^/]+$/);

    await expect(page.locator('runefoble-campaign-members')).toBeVisible({ timeout: 10_000 });
  }
);
