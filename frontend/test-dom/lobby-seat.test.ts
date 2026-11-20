/**
 * App Shell lobby seat (TASK-0889). The lobby renders in a real Chromium DOM.
 *
 * The Take a Seat control follows the `play` and `run_session` flags of the server reply.
 * When the player takes a seat, the shell calls the gateway join route and reads the roster
 * again. The tests stub `fetch` only, because the gateway is the process boundary.
 * Governing ADRs: ADR-0004, ADR-0013, ADR-0014. User story: US-0065.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { render } from 'lit';
import '@runefoble/game-session-ui/lobby/session-lobby';
import { renderLobby } from '../src/views/lobby-view.ts';
import type { RunefobleApp } from '../src/runefoble-app.ts';

const SESSION = 'sess-1';
const CAMPAIGN = 'camp-1';
const PLAYER = 'player-mira';
const CHARACTER = { id: 'char-mira', name: 'Mira Thornwake', characterClass: 'Ranger', level: 3, ownerId: PLAYER };

type Caps = { play: boolean; run_session: boolean };

function appFor(caps: Caps, participants: unknown[] = []): RunefobleApp {
  return {
    sessionId: SESSION,
    campaignId: CAMPAIGN,
    sessionTitle: 'Lantern Night',
    currentUserId: PLAYER,
    lobbyParticipants: participants,
    lobbyAvailableCharacters: [CHARACTER],
    characters: [],
    campaignCapabilities: { manage: false, view: true, ...caps },
    sessionSocket: { current: null },
    showToast: vi.fn(),
  } as unknown as RunefobleApp;
}

let host: HTMLElement | undefined;

async function mountLobby(app: RunefobleApp): Promise<HTMLElement & { updateComplete: Promise<boolean> }> {
  host = document.createElement('div');
  document.body.append(host);
  render(renderLobby(app), host);
  const lobby = host.querySelector('runefoble-session-lobby') as HTMLElement & { updateComplete: Promise<boolean> };
  await lobby.updateComplete;
  return lobby;
}

function seatButton(lobby: HTMLElement): HTMLButtonElement | null {
  return lobby.shadowRoot?.querySelector<HTMLButtonElement>('button.btn-take-seat') ?? null;
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

const SEATED_STATE = {
  session_id: SESSION,
  participants: {
    [PLAYER]: {
      player_id: PLAYER, character_id: CHARACTER.id, character_name: CHARACTER.name,
      character_class: CHARACTER.characterClass, is_present: true,
    },
  },
  lobby_readiness: {},
};

afterEach(() => {
  host?.remove();
  host = undefined;
  vi.restoreAllMocks();
});

describe('Take a Seat control', () => {
  it('shows for a caller who can play and has no seat', async () => {
    const lobby = await mountLobby(appFor({ play: true, run_session: false }));
    expect(seatButton(lobby)).not.toBeNull();
  });

  it('does not show for the person who runs the session', async () => {
    const lobby = await mountLobby(appFor({ play: true, run_session: true }));
    expect(seatButton(lobby)).toBeNull();
  });

  it('does not show for a caller who is already seated', async () => {
    const seated = { userId: PLAYER, username: 'Mira', role: 'player', isReady: false, isAbsent: false };
    const lobby = await mountLobby(appFor({ play: true, run_session: false }, [seated]));
    expect(seatButton(lobby)).toBeNull();
  });

  it('does not show for a caller without the play capability', async () => {
    const lobby = await mountLobby(appFor({ play: false, run_session: false }));
    expect(seatButton(lobby)).toBeNull();
  });
});

describe('Taking a seat', () => {
  it('calls the gateway join route with the chosen character and refreshes the roster', async () => {
    const calls: Array<{ url: string; method: string; body: unknown }> = [];
    vi.spyOn(window, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      calls.push({ url, method: init?.method ?? 'GET', body: init?.body ? JSON.parse(String(init.body)) : null });
      if (url.endsWith(`/sessions/${SESSION}/join`)) return json(SEATED_STATE);
      if (url.endsWith(`/sessions/${SESSION}`)) return json(SEATED_STATE);
      if (url.endsWith(`/campaigns/${CAMPAIGN}/members`)) return json([{ user_id: PLAYER, username: 'Mira', role: 'player' }]);
      if (url.endsWith('/characters')) return json([CHARACTER]);
      return json({ detail: 'unexpected' }, 404);
    });
    const app = appFor({ play: true, run_session: false });
    const lobby = await mountLobby(app);

    seatButton(lobby)!.click();
    await vi.waitFor(() => expect(app.lobbyParticipants).toHaveLength(1));

    const join = calls.find((c) => c.url.endsWith(`/sessions/${SESSION}/join`));
    expect(join?.method).toBe('POST');
    expect(join?.body).toEqual({ character_id: CHARACTER.id, character_name: CHARACTER.name, character_class: CHARACTER.characterClass });
    expect(app.lobbyParticipants[0]).toMatchObject({ userId: PLAYER, role: 'player', isReady: false });
  });

  it('reports the owner refusal and keeps the roster', async () => {
    vi.spyOn(window, 'fetch').mockImplementation(async () => json({ detail: 'Permission denied' }, 403));
    const app = appFor({ play: true, run_session: false });
    const lobby = await mountLobby(app);

    seatButton(lobby)!.click();
    await vi.waitFor(() => expect(app.showToast).toHaveBeenCalled());

    expect(app.lobbyParticipants).toEqual([]);
  });
});
