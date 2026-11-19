/**
 * Lobby session state that the lobby and VTT steps share (TASK-0652, ADR-0014, ADR-0015).
 *
 * The Background creates the campaign and the session through the gateway and keeps the ids
 * from the replies. A session title in feature text is a label only. A step that names a
 * session must name the one that setup created, so the steps never derive an id from text.
 */

import { requireValue } from './guards';
import type { World } from './world';

const SESSION_TITLE_KEY = 'lobbySessionTitle';

/** Records the session that setup created, with the title that feature text uses for it. */
export function rememberLobbySession(world: World, title: string, sessionId: string): void {
  world.sessionId = sessionId;
  world.set(SESSION_TITLE_KEY, title);
}

/** The id of the session that setup created under `title`. Throws for any other title. */
export function lobbySessionId(world: World, title: string): string {
  const created = requireValue(
    world.get<string>(SESSION_TITLE_KEY),
    'No session. Run "Evelyn creates campaign ... with session ..." first.'
  );
  if (created !== title) {
    throw new Error(`Session "${title}" was not set up in this scenario. Setup created "${created}".`);
  }
  return requireValue(world.sessionId, `Session "${title}" has no id.`);
}

/** The lobby route of the session that setup created under `title`. */
export function lobbyRoute(world: World, title: string): string {
  const campaignId = requireValue(world.campaignId, 'No campaign. Run "Evelyn creates campaign" first.');
  return `#/campaigns/${campaignId}/lobby/${lobbySessionId(world, title)}`;
}

/** Stores the bearer token of a persona that signed in during setup. */
export function rememberPersonaToken(world: World, persona: string, token: string | undefined): void {
  world.set(`token:${persona.toLowerCase()}`, requireValue(token, `Persona "${persona}" has no bearer token.`));
}

/** The bearer token of a persona that signed in during setup. */
export function personaToken(world: World, persona: string): string {
  return requireValue(
    world.get<string>(`token:${persona.toLowerCase()}`),
    `No bearer token for "${persona}". A setup step must sign that persona in first.`
  );
}
