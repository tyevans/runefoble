/**
 * App Shell Session Actions (TASK-0643).
 *
 * Handles the lobby events that start a live session and activate an absentee stand-in.
 */

import { router } from '../router/index.ts';
import type { RunefobleApp } from '../runefoble-app.ts';
import { handleToggleStandIn } from '../vtt-mesh-handlers.ts';

/** Tells the session socket that the session started, then opens the live tabletop. */
export function launchSession(host: RunefobleApp, e: CustomEvent): void {
  const cId = e.detail?.campaignId || host.campaignId;
  const sId = e.detail?.sessionId || host.sessionId;
  if (!cId || !sId) {
    host.showToast('Session not launched. The campaign or session is not known.');
    return;
  }
  const socket = host.sessionSocket.current;
  if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: 'session_started', campaignId: cId, sessionId: sId }));
  router.navigate(`#/campaigns/${cId}/sessions/${sId}`);
}

/** Toggles the stand-in for a player. An absent player opens the directives drawer. */
export function toggleStandIn(host: RunefobleApp, e: CustomEvent): void {
  handleToggleStandIn(host, e, host.sessionSocket.current);
  if (e.detail?.isAbsent) {
    host.isAbsenteeDirectiveOpen = true;
    host.showToast('Stand-In Activated: Directives drawer opened');
  }
}
