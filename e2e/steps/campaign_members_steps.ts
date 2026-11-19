/**
 * Campaign Roster Management Gate Step Definitions (TASK-0840, addendum of TASK-0870).
 *
 * The overview step records the capabilities reply that the App Shell reads. The roster steps
 * wait for the member row, then check the invite, role and remove controls. A missing control
 * and a control shown by mistake both fail. Governed by ADR-0001, ADR-0014 and Hard Invariant 7.
 */

import { expect, type Page } from '@playwright/test';
import { When, Then } from '../support/fixtures';
import { findPersona, resolvePersonaKey } from '../support/personas';
import { openAndRecordCapabilities, recordedCapabilities } from '../support/campaign_capabilities';

const MEMBERS = 'runefoble-campaign-members';
function memberRow(page: Page, roleOrName: string) {
  const persona = findPersona(resolvePersonaKey(roleOrName));
  return page.locator(`${MEMBERS} .member-item[data-user-id="${persona.userId}"]`);
}

When('I open the overview of the campaign', async ({ page, world }) => {
  const campaignId = world.campaignId;
  if (!campaignId) throw new Error('No campaign. Run "campaign {string} exists" first.');
  await openAndRecordCapabilities(page, world, campaignId, `#/campaigns/${campaignId}`);
  await expect(page.locator(MEMBERS)).toBeVisible({ timeout: 15_000 });
});

Then('the server reports that I can manage the campaign', async ({ world }) => {
  expect(recordedCapabilities(world).manage).toBe(true);
});

Then('the server reports that I cannot manage the campaign', async ({ world }) => {
  expect(recordedCapabilities(world).manage).toBe(false);
});

Then('the roster shows the management controls for {string}', async ({ page }, roleOrName: string) => {
  const row = memberRow(page, roleOrName);
  await expect(row).toBeVisible({ timeout: 10_000 });
  await expect(page.locator(`${MEMBERS} button.btn-invite`)).toBeVisible();
  await expect(row.locator('select.role-select')).toBeVisible();
  await expect(row.locator('button.btn-remove')).toBeVisible();
});

Then('the roster hides the management controls for {string}', async ({ page }, roleOrName: string) => {
  const row = memberRow(page, roleOrName);
  await expect(row).toBeVisible({ timeout: 10_000 });
  await expect(row.locator('.badge-role')).toBeVisible();
  await expect(page.locator(`${MEMBERS} button.btn-invite`)).toHaveCount(0);
  await expect(page.locator(`${MEMBERS} select.role-select`)).toHaveCount(0);
  await expect(page.locator(`${MEMBERS} button.btn-remove`)).toHaveCount(0);
});
