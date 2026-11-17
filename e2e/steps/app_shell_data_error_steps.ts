/**
 * App Shell Data Error Step Definitions (TASK-0640).
 * Governed by ADR-0014. Assertions use only observable UI output.
 */

import { expect } from '@playwright/test';
import { Then } from '../support/fixtures';

Then('the page should show the not-found state', async ({ page }) => {
  await expect(
    page.locator('runefoble-data-error h2', { hasText: 'Not found' })
  ).toBeVisible({ timeout: 10_000 });
});

Then('the page should not show {string}', async ({ page }, text: string) => {
  await expect(page.getByText(text, { exact: false })).toHaveCount(0);
});
