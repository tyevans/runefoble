/**
 * App Shell Title Resolvers (TASK-0640b).
 *
 * Resolves breadcrumb titles for campaigns, characters, sessions, and lobbies. A failed
 * read yields no title, so the breadcrumb falls back to the route identifier.
 */

import { router } from '../router/index.ts';
import type { RunefobleApp } from '../runefoble-app.ts';
import { appDataService } from '../services/app-data-service.ts';
import type { DataResult } from '../services/data-result.ts';

function titleOf<T>(result: DataResult<T>, pick: (value: T) => string | undefined): string | undefined {
  return result.ok ? pick(result.data) : undefined;
}

/** Installs the synchronous and asynchronous breadcrumb title resolvers on the router. */
export function installTitleResolvers(host: RunefobleApp): void {
  router.setTitleResolver((type, id) => (type === 'character' ? host.characters.find((c) => c.id === id)?.name : type === 'lobby' ? `Lobby ${id}` : undefined));
  router.setAsyncTitleResolver(async (type, id) => {
    if (type === 'campaign') return titleOf(await appDataService.fetchCampaign(id), (c) => c.title);
    if (type === 'character') return titleOf(await appDataService.fetchCharacter(id), (c) => c.name);
    if (type === 'session' || type === 'lobby') return titleOf(await appDataService.fetchSession(id), (s) => s.title);
    return undefined;
  });
}
