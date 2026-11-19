/**
 * View controller for the OBS party vitals route (TASK-0823 review).
 *
 * The route `#/overlay/party-vitals/:sessionId?position=&easing=&duration=` renders the page
 * element with the session id and the parsed query. The shell chrome is not rendered for it.
 */

import { html, type TemplateResult } from 'lit';
import type { RunefobleApp } from '../runefoble-app.ts';
import { parsePartyVitalsOverlayQuery } from '../app/party-vitals-overlay.ts';

export function renderPartyVitalsOverlay(app: RunefobleApp): TemplateResult {
  const options = parsePartyVitalsOverlayQuery(app.currentRoute?.query ?? {});
  return html`<runefoble-party-vitals-page
    session-id=${app.routeParams.sessionId ?? ''}
    position=${options.position}
    easing=${options.easing}
    .duration=${options.durationMs}
  ></runefoble-party-vitals-page>`;
}
