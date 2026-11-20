/**
 * Lobby State Step Definitions (TASK-0952).
 *
 * The steps check what a reload shows. The reload reads the readiness and the presence that
 * game_session stored, so the steps never read a value that the page kept. Setup uses public
 * gateway routes and the persona sign-in, as the other lobby steps do. Governed by ADR-0014,
 * ADR-0015 and Hard Invariant 7.
 */

import { expect, test, type Locator } from '@playwright/test';
import { Given, When, Then } from '../support/fixtures';
import { requireValue } from '../support/guards';
import { personaToken } from '../support/lobby_session';

const LOBBY = 'runefoble-session-lobby';

/** The lobby card of one participant, matched by its name. Strict mode fails on zero or several cards. */
function participantCard(lobby: Locator, name: string): Locator {
  return lobby.locator('.participant-card').filter({
    has: lobby.page().locator('.username', { hasText: new RegExp(name, 'i') }),
  });
}

When('{word} reloads the lobby page', async ({ world }, persona: string) => {
  const page = world.getPage(persona);
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page.locator(`${LOBBY} .lobby-header`)).toBeVisible({ timeout: 15_000 });
  // The roster comes from the owner. The step waits until the first seat card is drawn.
  await expect(page.locator(`${LOBBY} .participant-card`).first()).toBeVisible({ timeout: 15_000 });
});

Then('the {string} box of {word} is checked', async ({ world }, label: string, persona: string) => {
  const page = world.getPage(persona);
  const card = participantCard(page.locator(LOBBY), persona);
  await expect(card.getByRole('checkbox', { name: label, exact: true })).toBeChecked({ timeout: 10_000 });
});

Then(
  "{word}'s lobby shows {word} as {string}",
  async ({ world }, viewer: string, persona: string, status: string) => {
    const lobby = world.getPage(viewer).locator(LOBBY);
    await expect(participantCard(lobby, persona).locator('.badge-readiness')).toHaveText(status, {
      timeout: 10_000,
    });
  }
);

Then(
  "{word}'s lobby shows the {string} badge on the card of {word}",
  async ({ world }, viewer: string, badge: string, persona: string) => {
    const lobby = world.getPage(viewer).locator(LOBBY);
    await expect(participantCard(lobby, persona).locator('.badge-readiness')).toHaveText(badge, {
      timeout: 10_000,
    });
  }
);

When(
  '{word} checks {string} on the card of {word}',
  async ({ world }, persona: string, label: string, seat: string) => {
    const page = world.getPage(persona);
    const card = participantCard(page.locator(LOBBY), seat);
    const checkbox = card.getByRole('checkbox', { name: label, exact: true });
    await expect(checkbox).toHaveCount(1, { timeout: 10_000 });
    await checkbox.check();
  }
);

Then('{word} sees {string} in the lobby', async ({ world }, persona: string, text: string) => {
  const hint = world.getPage(persona).locator(`${LOBBY} .launch-hint`);
  await expect(hint).toHaveText(text, { timeout: 10_000 });
});
