/**
 * Session Lobby and VTT Background Steps (TASK-0652).
 *
 * Each scenario creates its own data through public gateway routes: Evelyn creates the campaign
 * and the session, each player redeems a player invite, creates a character and takes a seat
 * through the join route (TASK-0889). Each persona signs in through Zitadel in its own browser.
 * The steps keep the ids from the replies. Governed by ADR-0007, ADR-0014, ADR-0015 and
 * Hard Invariant 7. No step reads or writes private state.
 */

import { expect, test } from '@playwright/test';
import { Given } from '../support/fixtures';
import { requireValue } from '../support/guards';
import {
  lobbyRoute,
  lobbySessionId,
  personaToken,
  rememberLobbySession,
  rememberPersonaToken,
} from '../support/lobby_session';

const LOBBY = 'runefoble-session-lobby';

Given(
  'Evelyn creates campaign {string} with session {string} through the gateway',
  async ({ auth, frontdoorApi, world, page }, campaignTitle: string, sessionTitle: string) => {
    const evelyn = await auth.signInAs('evelyn', page);
    world.currentUser = evelyn;
    world.setPage('evelyn', page);
    rememberPersonaToken(world, 'evelyn', evelyn.token);
    const token = personaToken(world, 'evelyn');

    const campaign = await frontdoorApi.createCampaign(campaignTitle, { token });
    world.campaignId = requireValue(campaign.id, 'The campaign reply has no id.');
    world.campaignTitle = campaign.title;

    const session = await frontdoorApi.createCampaignSession(world.campaignId, sessionTitle, token);
    rememberLobbySession(world, sessionTitle, requireValue(session.id, 'The session reply has no id.'));
  }
);

Given(
  'Valeros and Sarah redeem a player invite to the campaign in separate browsers',
  async ({ browser, auth, frontdoorApi, world }) => {
    const campaignId = requireValue(world.campaignId, 'No campaign. Run "Evelyn creates campaign" first.');
    const dmToken = personaToken(world, 'evelyn');

    for (const persona of ['valeros', 'sarah']) {
      const context = await browser.newContext({ baseURL: test.info().project.use.baseURL });
      world.extraContexts.push(context);
      const personaPage = await context.newPage();
      world.setPage(persona, personaPage);
      const user = await auth.signInAs(persona, personaPage);
      rememberPersonaToken(world, persona, user.token);

      const invite = await frontdoorApi.createCampaignInvite(campaignId, 'player', dmToken);
      const inviteToken = requireValue(invite.token, 'The invite reply has no token.');
      const joined = await frontdoorApi.joinCampaign(inviteToken, personaToken(world, persona));
      expect(joined.role, `${persona} must join the campaign as a player`).toBe('player');
    }
  }
);

Given(
  '{word} takes a seat in {string} with a new character {string}',
  async ({ frontdoorApi, world }, persona: string, sessionTitle: string, characterName: string) => {
    const sessionId = lobbySessionId(world, sessionTitle);
    const token = personaToken(world, persona);
    // No `level`: character_sheet stores no level at creation (TASK-0905 changes that).
    const created = await frontdoorApi.createCharacter(
      { name: characterName, characterClass: 'Fighter', maxHp: 24, currentHp: 24, armorClass: 16, speed: 30 },
      token
    );
    const characterId = requireValue(created.id, 'The character reply has no id.');
    await frontdoorApi.joinSession(
      sessionId,
      { id: characterId, name: characterName, characterClass: 'Fighter' },
      token
    );
  }
);

Given('{word} opens the lobby of {string}', async ({ world }, persona: string, sessionTitle: string) => {
  const personaPage = world.getPage(persona);
  await personaPage.goto(lobbyRoute(world, sessionTitle));
  await personaPage.waitForLoadState('domcontentloaded');
  await expect(personaPage.locator(`${LOBBY} .lobby-header`)).toBeVisible({ timeout: 15_000 });
});
