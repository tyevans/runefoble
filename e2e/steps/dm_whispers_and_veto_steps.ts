/**
 * DM Whisper Bar and Veto Step Definitions (TASK-0949).
 *
 * Setup uses public gateway routes and the App Shell. The veto scenario proposes the AI action
 * with the public propose route and the DM's token (DoR item 8). Each assertion reads what the
 * DM sees in the whisper bar, or a public read route. No step changes state behind the UI.
 * Governed by ADR-0002, ADR-0014, ADR-0015 and Hard Invariant 7.
 */

import { expect, test, type APIRequestContext, type Locator } from '@playwright/test';
import { Given, When, Then } from '../support/fixtures';
import { bearerHeader } from '../support/frontdoor_api';
import { API_BASE_URL } from '../support/env';
import { assertOk, requireValue } from '../support/guards';
import { lobbySessionId, personaToken } from '../support/lobby_session';
import type { World } from '../support/world';

const BAR = 'runefoble-dm-whisper-bar';
const NO_MODEL = 'none';
const ACTION_KEY = 'whisperBarAction';

interface ProposedAction { actionId: string; expiresAt: number }
interface ListedWhisper { whisper_id: string; whisper_type: string; content: string; metadata?: { source?: string } }

function base(): string {
  return API_BASE_URL.replace(/\/$/, '');
}

function scopeQuery(world: World): string {
  const sessionId = requireValue(world.sessionId, 'No session. Run "Evelyn creates campaign" first.');
  const campaignId = requireValue(world.campaignId, 'No campaign. Run "Evelyn creates campaign" first.');
  return new URLSearchParams({ session_id: sessionId, campaign_id: campaignId }).toString();
}

async function listWhispers(request: APIRequestContext, world: World): Promise<{ whispers: ListedWhisper[]; narration_engine: string }> {
  const res = await request.get(`${base()}/api/v1/watcher/whispers?${scopeQuery(world)}`, { headers: bearerHeader(personaToken(world, 'evelyn')) });
  await assertOk(res, 'GET /api/v1/watcher/whispers');
  return res.json();
}

function bar(world: World): Locator {
  return world.getPage('evelyn').locator(BAR);
}

Given('the stack has no language model for narration', async ({ request, world }) => {
  const { narration_engine: engine } = await listWhispers(request, world);
  test.skip(engine !== NO_MODEL, `The stack narration engine is "${engine}". This scenario needs RUNEFOBLE_WATCHER_NARRATION_ENGINE=none.`);
});

Given('the stack has a language model for narration', async ({ request, world }) => {
  const { narration_engine: engine } = await listWhispers(request, world);
  test.skip(engine === NO_MODEL, 'The stack has no narration engine. This scenario needs RUNEFOBLE_WATCHER_NARRATION_ENGINE=inference_worker.');
});

Given(
  'The Watcher proposes {string} for {string} with a {int} second pause window',
  async ({ request, world }, description: string, title: string, seconds: number) => {
    const sessionId = lobbySessionId(world, title);
    const res = await request.post(`${base()}/api/v1/watcher/actions/propose`, {
      headers: { 'Content-Type': 'application/json', ...bearerHeader(personaToken(world, 'evelyn')) },
      data: {
        session_id: sessionId,
        campaign_id: requireValue(world.campaignId, 'No campaign.'),
        actor_name: 'Goblin',
        action_type: 'move',
        description,
        pause_window_ms: seconds * 1000,
      },
    });
    await assertOk(res, 'POST /api/v1/watcher/actions/propose');
    const body = await res.json();
    world.set(ACTION_KEY, { actionId: body.action_id, expiresAt: body.expires_at } satisfies ProposedAction);
  }
);

When('Evelyn asks for a whisper in the whisper bar', async ({ world }) => {
  const page = world.getPage('evelyn');
  const reply = page.waitForResponse(
    (r) => r.request().method() === 'POST' && new URL(r.url()).pathname === '/api/v1/watcher/whispers/generate',
    { timeout: 30_000 }
  );
  await bar(world).getByRole('button', { name: 'Ask for a whisper' }).click();
  const answer = await reply;
  expect(answer.ok(), `/api/v1/watcher/whispers/generate answered ${answer.status()}`).toBe(true);
});

When('Evelyn clicks Veto on the pending action in the whisper bar', async ({ world }) => {
  const page = world.getPage('evelyn');
  const veto = bar(world).getByRole('button', { name: 'Veto', exact: true });
  await expect(veto).toHaveCount(1, { timeout: 15_000 });
  const reply = page.waitForResponse(
    (r) => r.request().method() === 'POST' && new URL(r.url()).pathname === '/api/v1/watcher/veto',
    { timeout: 15_000 }
  );
  await veto.click();
  const answer = await reply;
  expect(answer.ok(), `/api/v1/watcher/veto answered ${answer.status()}`).toBe(true);
});

Then("Evelyn's whisper bar shows {string}", async ({ world }, text: string) => {
  await expect(bar(world).getByRole('status').filter({ hasText: text })).toBeVisible({ timeout: 15_000 });
});

Then("Evelyn's whisper bar shows no whisper", async ({ world }) => {
  await expect(bar(world).locator('.whisper-card')).toHaveCount(0);
  await expect(bar(world).locator('.empty-state')).toHaveText('No whispers yet.');
});

Then("Evelyn's whisper bar shows the model whisper that the gateway lists", async ({ request, world }) => {
  const { whispers } = await listWhispers(request, world);
  const fromModel = whispers.filter((w) => w.whisper_type === 'narration' && w.metadata?.source === 'llm');
  expect(fromModel.length, 'The gateway lists no whisper from the language model.').toBeGreaterThan(0);
  const card = bar(world).locator('.whisper-card[data-whisper-type="narration"] .whisper-content');
  await expect(card.first()).toHaveText(fromModel[0].content, { timeout: 15_000 });
});

Then("Evelyn's whisper bar shows the action as vetoed", async ({ world }) => {
  await expect(bar(world).locator('[data-action-status="vetoed"] .action-outcome')).toHaveText(/vetoed/i, { timeout: 10_000 });
  await expect(bar(world).getByRole('button', { name: 'Veto', exact: true })).toHaveCount(0);
});

Then('after the pause window the action is still vetoed', async ({ request, world }) => {
  const action = requireValue(world.get<ProposedAction>(ACTION_KEY), 'No proposed action.');
  const waitMs = Math.max(0, action.expiresAt * 1000 - Date.now()) + 2_000;
  await new Promise((resolve) => setTimeout(resolve, waitMs));
  const res = await request.get(`${base()}/api/v1/watcher/actions/pending?${scopeQuery(world)}`, { headers: bearerHeader(personaToken(world, 'evelyn')) });
  await assertOk(res, 'GET /api/v1/watcher/actions/pending');
  const actions: { action_id: string; status: string }[] = await res.json();
  expect(actions.find((a) => a.action_id === action.actionId)?.status).toBe('vetoed');
});
