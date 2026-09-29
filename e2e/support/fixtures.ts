/**
 * Runefoble Playwright-BDD Fixtures Aggregator
 * Exposes world context, auth fixtures, and frontdoor API to BDD steps.
 * Governed by ADR-0014 and Hard Invariant 7.
 */

import { test as baseTest, createBdd } from 'playwright-bdd';
import { World } from './world';
import { AuthFixtures } from './auth_fixtures';
import { FrontdoorApi } from './frontdoor_api';

export type BddCustomFixtures = {
  world: World;
  auth: AuthFixtures;
  frontdoorApi: FrontdoorApi;
};

export const test = baseTest.extend<BddCustomFixtures>({
  world: async ({}, use) => {
    const world = new World();
    await use(world);
    world.reset();
  },
  auth: async ({ page, context }, use) => {
    const auth = new AuthFixtures(page, context);
    await use(auth);
  },
  frontdoorApi: async ({ request }, use) => {
    const api = new FrontdoorApi(request);
    await use(api);
  },
});

export const { Given, When, Then, Before, After, Step } = createBdd(test);
