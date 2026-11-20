/**
 * Steps for the invite link that opens the join view in the App Shell (TASK-0950, ADR-0023).
 *
 * Setup and assertions use the App Shell and the Zitadel hosted pages only. The account mail
 * is read from Mailpit in the local render. No step calls the API join route.
 */

import { expect, type Page } from '@playwright/test';
import { Given, When, Then } from '../support/fixtures';
import { requireValue } from '../support/guards';
import { joinCampaignThroughInviteLink } from '../support/invite_join';
import { extractZitadelLink, waitForMailText } from '../support/mailpit';
import { signInWithZitadel } from '../support/zitadel_login';

const INVITE_URL = 'inviteUrl';
const INVITE_TOKEN = 'inviteToken';
const INVITE_EMAIL = 'inviteEmail';
const INVITE_PASSWORD = 'invitePassword';
const MEMBERS = 'runefoble-campaign-members';
const JOIN = 'runefoble-campaign-join';

/** The token is the part of the link after `#/join/`. The link itself is an absolute URL. */
function tokenFromLink(link: string): string {
  const token = new URL(link).hash.replace(/^#\/join\//, '');
  return requireValue(token || null, 'The invite link has no token.');
}

function membersModal(page: Page) {
  return page.locator(`${MEMBERS} .modal-card`);
}

async function openInviteModal(page: Page): Promise<void> {
  const modal = membersModal(page);
  if (await modal.isVisible()) return;
  const inviteBtn = page
    .locator(`${MEMBERS} header.members-header`)
    .getByRole('button', { name: 'Invite Adventurers', exact: true });
  await expect(inviteBtn).toBeVisible({ timeout: 10_000 });
  await inviteBtn.click();
  await expect(modal).toBeVisible({ timeout: 10_000 });
}

async function generatePlayerLink(page: Page): Promise<string> {
  await openInviteModal(page);
  const modal = membersModal(page);
  await modal.locator('#invite-role-select').selectOption({ value: 'player' });
  const linkInput = modal.locator('.invite-link-input');
  const previous = (await linkInput.count()) > 0 ? await linkInput.inputValue() : '';
  await modal.getByRole('button', { name: 'Generate Link', exact: true }).click();
  // Accept only a link that this click produced. A link from an earlier invite is never the new one (TASK-0973).
  await expect
    .poll(async () => ((await linkInput.count()) > 0 ? linkInput.inputValue() : ''), { timeout: 10_000 })
    .toMatch(/#\/join\//);
  const link = await linkInput.inputValue();
  expect(link).not.toBe(previous);
  return link;
}

function storeInviteLink(world: { set(key: string, value: unknown): void }, link: string): void {
  world.set(INVITE_URL, link);
  world.set(INVITE_TOKEN, tokenFromLink(link));
}

Given('Evelyn creates campaign {string} in the UI', async ({ auth, page, world }, title: string) => {
  world.currentUser = await auth.signInAs('evelyn', page);
  world.setPage('evelyn', page);
  world.campaignTitle = title;

  await page.goto('#/campaigns');
  const newBtn = page
    .locator('runefoble-campaign-dashboard header.dashboard-header')
    .getByRole('button', { name: '+ New Campaign', exact: true });
  await expect(newBtn).toBeVisible({ timeout: 15_000 });
  await newBtn.click();

  const creator = page.locator('runefoble-campaign-creator');
  await creator.locator('#campaign-title').fill(title);
  await creator.locator('#campaign-setting').fill('Northrend');
  await creator.getByRole('button', { name: 'Create Campaign', exact: true }).click();

  await expect
    .poll(async () => page.evaluate(() => window.location.hash), { timeout: 15_000 })
    .toMatch(/^#\/campaigns\/[^/]+$/);
  world.campaignId = await page.evaluate(() => window.location.hash.replace(/^#\/campaigns\//, ''));
  await expect(page.locator(MEMBERS)).toBeVisible({ timeout: 15_000 });
});

When('Evelyn opens {string} for the campaign', async ({ page }, buttonName: string) => {
  const inviteBtn = page
    .locator(`${MEMBERS} header.members-header`)
    .getByRole('button', { name: buttonName, exact: true });
  await expect(inviteBtn).toBeVisible({ timeout: 10_000 });
  await inviteBtn.click();
  await expect(membersModal(page)).toBeVisible({ timeout: 10_000 });
});

Then('no shareable link field is shown', async ({ page }) => {
  await expect(membersModal(page)).toBeVisible({ timeout: 10_000 });
  await expect(page.locator(`${MEMBERS} .invite-link-input`)).toHaveCount(0);
});

Given('Evelyn generates a player invite link in the UI', async ({ page, world }) => {
  storeInviteLink(world, await generatePlayerLink(page));
});

Given('Evelyn generates a player invite link in the UI and copies it', async ({ page, world }) => {
  const link = await generatePlayerLink(page);
  const modal = membersModal(page);
  await modal.getByRole('button', { name: 'Copy Link', exact: true }).click();
  await expect(modal.locator('.copied-badge')).toBeVisible({ timeout: 10_000 });
  // The clipboard holds the same full URL as the field (playwright.config.ts grants clipboard access).
  const clipboard = await page.evaluate(() => navigator.clipboard.readText());
  expect(clipboard).toBe(link);
  storeInviteLink(world, clipboard);
});

Then('the copied link starts with the App Shell origin and contains {string}', async ({ page, world }, fragment: string) => {
  const link = requireValue(world.get<string>(INVITE_URL), 'No invite link. Generate one first.');
  expect(new URL(link).origin).toBe(new URL(page.url()).origin);
  expect(link).toContain(fragment);
});

Then('the copied link does not contain {string}', async ({ world }, forbidden: string) => {
  const link = requireValue(world.get<string>(INVITE_URL), 'No invite link. Generate one first.');
  expect(link).not.toContain(forbidden);
});

When('Sarah opens the copied invite link in a new browser context', async ({ browser, world }) => {
  const link = requireValue(world.get<string>(INVITE_URL), 'No invite link. Generate one first.');
  const context = await browser.newContext();
  world.extraContexts.push(context);
  const page = await context.newPage();
  world.setPage('sarah', page);
  await page.goto(link);
  await expect(page.locator(JOIN)).toBeVisible({ timeout: 15_000 });
});

When('Sarah creates an account from the invite', async ({ world }) => {
  const page = world.getPage('sarah');
  const email = `invitee-${Date.now()}@example.test`;
  world.set(INVITE_EMAIL, email);
  const join = page.locator(JOIN);
  await join.locator('input[name="displayName"]').fill('Sarah Invitee');
  await join.locator('input[name="email"]').fill(email);
  await join.getByRole('button', { name: 'Create account', exact: true }).click();
  await expect(join.getByText('Check Your E-mail', { exact: true })).toBeVisible({ timeout: 15_000 });
});

When('Sarah reads the Zitadel e-mail and sets a password', async ({ request, world }) => {
  const page = world.getPage('sarah');
  const email = requireValue(world.get<string>(INVITE_EMAIL), 'No account e-mail. Create the account first.');
  const password = `Invite-${Date.now()}-Pass!`;
  world.set(INVITE_PASSWORD, password);

  const link = extractZitadelLink(await waitForMailText(request, email));
  await page.goto(link);
  // The hosted Zitadel page sets the password. Runefoble never sees it (ADR-0023 b).
  await page.locator('#password').fill(password);
  await page.locator('#passwordconfirm').fill(password);
  await page.locator('#init-button').click();
});

When('Sarah completes the Zitadel sign-in', async ({ world }) => {
  const page = world.getPage('sarah');
  const email = requireValue(world.get<string>(INVITE_EMAIL), 'No account e-mail. Create the account first.');
  const password = requireValue(world.get<string>(INVITE_PASSWORD), 'No password. Set the password first.');
  // The invite page is open again. Its sign-in button opens the modal, and the Zitadel sign-in returns to the join route.
  await page.goto(`/#/join/${requireValue(world.get<string>(INVITE_TOKEN), 'No invite token.')}`);
  await page.locator(JOIN).getByRole('button', { name: 'I already have an account', exact: true }).click();
  const outcome = await signInWithZitadel(page, email, password);
  expect(outcome).toEqual({ kind: 'session' });
});

When('Sarah joins the campaign from the invite page', async ({ world }) => {
  const page = world.getPage('sarah');
  world.campaignId = await joinCampaignThroughInviteLink(page, requireValue(world.get<string>(INVITE_TOKEN), 'No invite token.'));
});

Then('Sarah sees the campaign {string} with the role {string}', async ({ world }, title: string, role: string) => {
  const page = world.getPage('sarah');
  await expect(page.locator('runefoble-campaign-header')).toContainText(title, { timeout: 15_000 });
  // The header shows the stored role value (for example `player`), so the check ignores case.
  await expect(page.locator('runefoble-header')).toContainText(new RegExp(`\\b${role}\\b`, 'i'), { timeout: 15_000 });
});

Then('the campaign list of Sarah shows {string}', async ({ world }, title: string) => {
  const page = world.getPage('sarah');
  await page.goto('#/campaigns');
  await expect(page.locator('runefoble-campaign-dashboard')).toContainText(title, { timeout: 15_000 });
});

Given('Sarah is signed in', async ({ auth, page, world }) => {
  world.currentUser = await auth.signInAs('sarah', page);
  world.setPage('sarah', page);
});

When('Sarah opens the link {string} and asks to join', async ({ world }, link: string) => {
  const page = world.getPage('sarah');
  await page.goto(`/${link}`);
  const joinButton = page.locator(JOIN).getByRole('button', { name: 'Join campaign', exact: true });
  await expect(joinButton).toBeVisible({ timeout: 15_000 });
  await joinButton.click();
});

Then('Sarah sees the refusal from the server', async ({ world }) => {
  const page = world.getPage('sarah');
  await expect(page.locator(`${JOIN} [role="alert"]`)).toBeVisible({ timeout: 15_000 });
});

Then('Sarah is not added to any campaign', async ({ world }) => {
  const page = world.getPage('sarah');
  // The refused join keeps the person on the join route. No campaign route opens.
  expect(await page.evaluate(() => window.location.hash)).toMatch(/^#\/join\//);
});
