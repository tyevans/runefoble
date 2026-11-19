/**
 * App Shell View Resolver (TASK-0643).
 *
 * Maps a matched route to the view id that the App Shell renders. The module is pure.
 * It has no DOM access. The App Shell and the view wiring tests import this one mapping.
 */

import type { MatchedRoute } from './router.ts';

export type AppActiveView =
  | 'login'
  | 'campaigns'
  | 'campaign-detail'
  | 'campaign-characters'
  | 'campaign-codex'
  | 'campaign-analytics'
  | 'campaign-forge'
  | 'characters'
  | 'character-sheet'
  | 'session-lobby'
  | 'session-active'
  | 'profile'
  | 'caravan-board'
  | 'party-vitals-overlay'
  | 'rules';

const CAMPAIGN = '#/campaigns/:campaignId';

/** Returns the view id for a route. An unknown or missing route resolves to the campaign hub. */
export function resolveActiveView(route: Pick<MatchedRoute, 'pattern'> | null): AppActiveView {
  const pat = route?.pattern || '';
  if (pat === '#/login' || pat === '#/register') return 'login';
  if (pat.startsWith(`${CAMPAIGN}/lobby/`)) return 'session-lobby';
  if (pat.startsWith(`${CAMPAIGN}/sessions/`)) return 'session-active';
  if (pat === `${CAMPAIGN}/characters`) return 'campaign-characters';
  if (pat === `${CAMPAIGN}/codex`) return 'campaign-codex';
  if (pat === `${CAMPAIGN}/analytics`) return 'campaign-analytics';
  if (pat === `${CAMPAIGN}/forge`) return 'campaign-forge';
  if (pat.startsWith(CAMPAIGN)) return 'campaign-detail';
  if (pat === '#/characters') return 'characters';
  if (pat.startsWith('#/characters/')) return 'character-sheet';
  if (pat === '#/profile') return 'profile';
  if (pat === '#/rules') return 'rules';
  if (pat === '#/caravans/:sharedWorldId') return 'caravan-board';
  if (pat === '#/overlay/party-vitals/:sessionId') return 'party-vitals-overlay';
  return 'campaigns';
}
