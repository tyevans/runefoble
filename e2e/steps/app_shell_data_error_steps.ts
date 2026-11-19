/**
 * App Shell Data Error Step Definitions (TASK-0640, TASK-0909).
 * Governed by ADR-0014. Assertions use only observable UI output.
 */

import { expect } from '@playwright/test';
import { Then } from '../support/fixtures';
import { exactText } from '../support/guards';

Then('the page should show the not-found state', async ({ page }) => {
  await expect(
    page.locator('runefoble-data-error h2', { hasText: 'Not found' })
  ).toBeVisible({ timeout: 10_000 });
});

Then('the page should not show {string}', async ({ page }, text: string) => {
  await expect(page.getByText(text, { exact: false })).toHaveCount(0);
});

// The roster empty state, not a placeholder card. The roster's own help text says "adventurer",
// so this step counts cards and matches the whole empty-state heading (TASK-0909).
Then('the character roster shows the empty state {string}', async ({ page }, heading: string) => {
  const roster = page.locator('runefoble-character-roster');
  await expect(roster.locator('.empty-roster h3', { hasText: exactText(heading) })).toBeVisible({ timeout: 10_000 });
  await expect(roster.locator('article.character-card')).toHaveCount(0);
});
