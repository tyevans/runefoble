/**
 * Rules Compendium Route Playwright BDD Step Definitions (TASK-0648).
 *
 * Drives <runefoble-rules-compendium> on #/rules through its search input. Governed by
 * ADR-0014 and Hard Invariant 7. The steps set up nothing and use no backdoor.
 */

import { expect } from '@playwright/test';
import { When, Then } from '../support/fixtures';

const COMPENDIUM = 'runefoble-rules-compendium';

When('I search the rules compendium for {string}', async ({ page }, query: string) => {
  await page.waitForSelector(COMPENDIUM, { timeout: 15_000 });
  const input = page.locator(`${COMPENDIUM} input.search-input`);
  await input.fill(query);
  await input.press('Enter');
});

Then('the rules compendium results list contains {string}', async ({ page }, name: string) => {
  const result = page.locator(`${COMPENDIUM} .result-card .rule-title`, { hasText: name });
  // Justified .first(): a search can return several matching rules. The step asserts that at least one is listed.
  await expect(result.first()).toBeVisible({ timeout: 15_000 });
});
