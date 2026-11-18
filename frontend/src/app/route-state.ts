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
  | 'sessionId' | 'sessionTitle' | 'selectedCharacterId' | 'isAuthModalOpen'
>;

/** Applies the route to the host. A login or register route opens the auth modal. */
export function applyRouteState(host: RouteStateHost, route: MatchedRoute): void {
  const { campaignId = '', sessionId = '', characterId } = route.params;
  host.currentRoute = route;
  host.routeParams = route.params;
  host.breadcrumbs = route.breadcrumbs;
  host.campaignId = campaignId;
  host.campaignTitle = campaignId ? router.resolveTitle('campaign', campaignId) || '' : '';
  host.sessionId = sessionId;
  host.sessionTitle = sessionId ? router.resolveTitle('session', sessionId) || router.resolveTitle('lobby', sessionId) || '' : '';
  if (characterId) host.selectedCharacterId = characterId;
  if (route.pattern === '#/login' || route.pattern === '#/register') host.isAuthModalOpen = true;
}
