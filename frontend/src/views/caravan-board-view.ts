/**
 * Caravan Board View (TASK-0807). Mounts the vendored <runefoble-caravan-board> for one shared world.
 *
 * The route carries the shared-world id. The optional `campaign` and `party` query values name the
 * party that accepts and dispatches contracts. The board never picks a default party, so a route
 * without them sends empty values, and the owner refuses the action.
 *
 * The load reads the notice board through the gateway. A failed read sets the load error. The
 * view never shows substitute contracts.
 */

import { html, type TemplateResult } from 'lit';
import type { MatchedRoute } from '../router/index.ts';
import type { RunefobleApp } from '../runefoble-app.ts';
import { appDataService } from '../services/app-data-service.ts';
import { failLoad } from '../app/load-error.ts';

export async function loadCaravanBoard(host: RunefobleApp, route: MatchedRoute): Promise<void> {
  const res = await appDataService.fetchCaravanContracts(route.params.sharedWorldId ?? '');
  if (!res.ok) {
    host.caravanContracts = [];
    failLoad(host, res);
    return;
  }
  host.caravanContracts = res.data;
}

export function renderCaravanBoard(app: RunefobleApp): TemplateResult {
  const sharedWorldId = app.routeParams.sharedWorldId ?? '';
  const query = app.currentRoute?.query ?? {};
  return html`<div class="caravan-board-layout">
    <runefoble-caravan-board
      .sharedWorldId=${sharedWorldId}
      .campaignId=${query.campaign ?? ''}
      .partyName=${query.party ?? ''}
      .contracts=${app.caravanContracts}
    ></runefoble-caravan-board>
  </div>`;
}
