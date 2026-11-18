/**
 * Session Lobby View (TASK-0643). Renders the pre-game assembly lobby.
 */

import { html } from 'lit';
import type { RunefobleApp } from '../runefoble-app.ts';
import { handleToggleReadiness } from '../vtt-mesh-handlers.ts';
import { launchSession, toggleStandIn } from '../app/session-actions.ts';
import { selectCharacterFromEvent } from '../app/character-actions.ts';

export function renderLobby(app: RunefobleApp) {
  return html`<runefoble-session-lobby session-id=${app.sessionId} campaign-id=${app.campaignId} session-title=${app.sessionTitle} current-user-id=${app.currentUserId} .participants=${app.lobbyParticipants} .availableCharacters=${app.lobbyAvailableCharacters} .isDm=${app.isDM} .canLaunch=${app.isDM} @select-character=${(e: CustomEvent) => selectCharacterFromEvent(app, e)} @character-selected=${(e: CustomEvent) => selectCharacterFromEvent(app, e)} @launch-session=${(e: CustomEvent) => launchSession(app, e)} @toggle-readiness=${(e: CustomEvent) => handleToggleReadiness(app, e, app.sessionSocket.current)} @toggle-stand-in=${(e: CustomEvent) => toggleStandIn(app, e)}></runefoble-session-lobby>`;
}
