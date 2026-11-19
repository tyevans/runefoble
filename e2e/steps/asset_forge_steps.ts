/**
 * Asset Forge and Print Forge Playwright BDD Step Definitions
 *
 * Drives the forge components through their UI and observes the public forge
 * routes they call. Setup goes through the page only. No route is faked: the
 * error path uses a request that asset_forge itself refuses (TASK-0840).
 * Governed by ADR-0014 and Hard Invariant 7. TASK-0613.
 */

import { expect, type Page, type Response } from '@playwright/test';
import { Given, When, Then } from '../support/fixtures';

interface RecordedPost {
  url: string;
  body: Record<string, unknown>;
}

/** Forge POST requests seen on each page, recorded from the start of the scenario. */
const postsByPage = new WeakMap<Page, RecordedPost[]>();

/** Successful forge replies seen on each page. Playwright keeps their bodies until the page closes. */
const repliesByPage = new WeakMap<Page, Response[]>();

/** Every forge POST reply seen on each page, as the URL and the HTTP status. */
const statusesByPage = new WeakMap<Page, Array<{ url: string; status: number }>>();

function postsFor(page: Page): RecordedPost[] {
  const posts = postsByPage.get(page);
  if (!posts) {
    throw new Error('Forge request recorder is not installed. Run "the asset forge is open" first.');
  }
  return posts;
}

Given('the asset forge is open', async ({ page, world }) => {
  const campaignId = world.campaignId;
  if (!campaignId) {
    throw new Error('No campaign is set. Run "campaign {string} exists" first.');
  }
  const posts: RecordedPost[] = [];
  const replies: Response[] = [];
  const statuses: Array<{ url: string; status: number }> = [];
  postsByPage.set(page, posts);
  repliesByPage.set(page, replies);
  statusesByPage.set(page, statuses);
  page.on('request', (request) => {
    if (request.method() === 'POST' && request.url().includes('/api/v1/forge/')) {
      posts.push({ url: request.url(), body: request.postDataJSON() as Record<string, unknown> });
    }
  });
  page.on('response', (response) => {
    if (response.request().method() !== 'POST' || !response.url().includes('/api/v1/forge/')) return;
    statuses.push({ url: response.url(), status: response.status() });
    if (response.ok()) replies.push(response);
  });
  await page.goto(`#/campaigns/${campaignId}/forge`);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForSelector('runefoble-asset-forge', { timeout: 15_000 });
});

When('I enter {string} as the battlemap prompt', async ({ page }, prompt: string) => {
  await page.locator('runefoble-asset-forge input.input-field').first().fill(prompt);
});

Then('the forge route {string} receives the prompt {string}', async ({ page }, path: string, prompt: string) => {
  await expect
    .poll(() => postsFor(page).some((post) => post.url.endsWith(path) && post.body.prompt === prompt))
    .toBe(true);
});

Then('the forge route {string} answers with status {int}', async ({ page }, path: string, status: number) => {
  const statuses = statusesByPage.get(page);
  if (!statuses) {
    throw new Error('Forge reply recorder is not installed. Run "the asset forge is open" first.');
  }
  await expect
    .poll(() => statuses.filter((reply) => new URL(reply.url).pathname === path).map((reply) => reply.status))
    .toEqual([status]);
});

Then('the forge route {string} receives a JSON export request', async ({ page }, path: string) => {
  await expect
    .poll(() => postsFor(page).some((post) => post.url.endsWith(path) && post.body.format === 'json'))
    .toBe(true);
});

Then('I should see the asset id returned by the forge', async ({ page }) => {
  const replies = repliesByPage.get(page);
  if (!replies) {
    throw new Error('Forge reply recorder is not installed. Run "the asset forge is open" first.');
  }
  const bodies = await Promise.all(replies.map((reply) => reply.json() as Promise<{ asset_id?: string }>));
  const assetIds = bodies.map((body) => body.asset_id).filter((id): id is string => typeof id === 'string');
  expect(assetIds.length).toBeGreaterThan(0);
  const shown = page.locator('[data-testid="forged-asset-id"]').first();
  await expect(shown).toContainText(assetIds[assetIds.length - 1]);
});

Then('I should see the image {string}', async ({ page }, alt: string) => {
  await expect(page.locator(`img[alt="${alt}"]`)).toBeVisible();
});

Then('I should not see the image {string}', async ({ page }, alt: string) => {
  await expect(page.locator(`img[alt="${alt}"]`)).toHaveCount(0);
});

Then('I should see the error {string}', async ({ page }, message: string) => {
  await expect(page.locator('[role="alert"]').filter({ hasText: message })).toBeVisible();
});

Then('I should see a download link for the PDF', async ({ page }) => {
  await expect(page.locator('a.download-link[download]')).toBeVisible();
});
