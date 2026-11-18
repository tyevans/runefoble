/**
 * Asset Forge and Print Forge Playwright BDD Step Definitions
 *
 * Drives the forge components through their UI and observes the public forge
 * routes they call. Setup goes through the page only. The only fault injection
 * is a 503 response at the network boundary, used to prove the error path.
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
  postsByPage.set(page, posts);
  repliesByPage.set(page, replies);
  page.on('request', (request) => {
    if (request.method() === 'POST' && request.url().includes('/api/v1/forge/')) {
      posts.push({ url: request.url(), body: request.postDataJSON() as Record<string, unknown> });
    }
  });
  page.on('response', (response) => {
    if (response.request().method() === 'POST' && response.url().includes('/api/v1/forge/') && response.ok()) {
      replies.push(response);
    }
  });
  await page.goto(`#/campaigns/${campaignId}/forge`);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForSelector('runefoble-asset-forge', { timeout: 15_000 });
});

Given('the forge route {string} responds with status {int}', async ({ page }, path: string, status: number) => {
  await page.route(`**${path}`, (route) =>
    route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Silo asset storage is unavailable. The asset was not stored.' }),
    })
  );
});

When('I enter {string} as the battlemap prompt', async ({ page }, prompt: string) => {
  await page.locator('runefoble-asset-forge input.input-field').first().fill(prompt);
});

Then('the forge route {string} receives the prompt {string}', async ({ page }, path: string, prompt: string) => {
  await expect
    .poll(() => postsFor(page).some((post) => post.url.endsWith(path) && post.body.prompt === prompt))
    .toBe(true);
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
