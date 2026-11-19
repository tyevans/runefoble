/**
 * App Shell Route State (TASK-0643).
 *
 * Copies a matched route into the shell state: route, params, breadcrumbs, and the
 * campaign, session, and character identifiers with their resolved titles.
 */

import { router, type MatchedRoute } from '../router/index.ts';
import type { RunefobleApp } from '../runefoble-app.ts';

type RouteStateHost = Pick<
  RunefobleApp,
  | 'currentRoute' | 'routeParams' | 'breadcrumbs' | 'campaignId' | 'campaignTitle'
  | 'sessionId' | 'sessionTitle' | 'selectedCharacterId' | 'isAuthModalOpen' | 'boardKind'
>;

/** Applies the route to the host. A login or register route opens the auth modal. A new session id resets the board to `loading`. */
export function applyRouteState(host: RouteStateHost, route: MatchedRoute): void {
  const { campaignId = '', sessionId = '', characterId } = route.params;
  host.currentRoute = route;
  host.routeParams = route.params;
  host.breadcrumbs = route.breadcrumbs;
  host.campaignId = campaignId;
  host.campaignTitle = campaignId ? router.resolveTitle('campaign', campaignId) || '' : '';
  // A new session has no board read yet. The view mounts no board, and so opens no board socket,
  // until the read answers. A socket opened before the board exists is refused and never reopens.
  if (sessionId !== host.sessionId) host.boardKind = 'loading';
  host.sessionId = sessionId;
  host.sessionTitle = sessionId ? router.resolveTitle('session', sessionId) || router.resolveTitle('lobby', sessionId) || '' : '';
  if (characterId) host.selectedCharacterId = characterId;
  if (route.pattern === '#/login' || route.pattern === '#/register') host.isAuthModalOpen = true;
}
