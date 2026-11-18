/**
 * App Shell Route Data Loader (TASK-0640b).
 *
 * Loads the data that each routed view needs. A failed read sets loadError, so the shell
 * shows an error state with retry. Session routes delegate to session-data-loader.ts.
 */

import { router, type MatchedRoute } from '../router/index.ts';
import type { RunefobleApp } from '../runefoble-app.ts';
import { appDataService } from '../services/app-data-service.ts';
import { failLoad } from './load-error.ts';
import { loadActiveSessionData, loadLobbyData } from './session-data-loader.ts';
import { loadAnalyticsData, loadCodexData } from './campaign-hub-data-loader.ts';

const CAMPAIGN_HUB_VIEWS: string[] = ['campaign-detail', 'campaign-characters', 'campaign-codex', 'campaign-analytics'];

/** Loads the data for the view that the host reports as active, and the campaign switcher. */
export async function loadRouteData(host: RunefobleApp, route: MatchedRoute): Promise<void> {
  host.loadError = null;
  const view = host.getActiveView();
  await Promise.all([
    view === 'login' || view === 'campaigns' ? undefined : loadCampaignSwitcher(host),
    loadViewData(host, route, view),
  ]);
}

async function loadViewData(host: RunefobleApp, route: MatchedRoute, view: string): Promise<void> {
  if (view === 'campaigns') await loadCampaigns(host);
  else if (CAMPAIGN_HUB_VIEWS.includes(view)) await loadCampaignHub(host, route);
  else if (view === 'characters') await loadRoster(host);
  else if (view === 'character-sheet') await loadCharacterSheet(host, route);
  else if (view === 'session-lobby') await loadLobbyData(host, route);
  else if (view === 'session-active') await loadActiveSessionData(host, route);
}

async function loadCampaigns(host: RunefobleApp): Promise<void> {
  const res = await appDataService.fetchCampaigns();
  if (!res.ok) return failLoad(host, res);
  host.campaigns = res.data;
}

/** Fills the header campaign switcher from the API. A failed read is reported as a toast. */
async function loadCampaignSwitcher(host: RunefobleApp): Promise<void> {
  const res = await appDataService.fetchCampaigns();
  if (res.ok) host.campaigns = res.data;
  else host.showToast(`Campaign list not loaded. ${res.message}`);
}

async function loadCampaignHub(host: RunefobleApp, route: MatchedRoute): Promise<void> {
  const c = route.params.campaignId ?? '';
  host.inviteUrl = '';
  host.inviteToken = '';
  const [camp, members, sessions, chars, rosterCamps] = await Promise.all([
    appDataService.fetchCampaign(c),
    appDataService.fetchCampaignMembers(c),
    appDataService.fetchCampaignSessions(c),
    appDataService.fetchCharacters(),
    appDataService.fetchRosterCampaignOptions(),
  ]);
  if (!camp.ok || !members.ok || !sessions.ok || !chars.ok || !rosterCamps.ok) {
    return failLoad(host, camp, members, sessions, chars, rosterCamps);
  }
  host.currentCampaign = camp.data;
  host.campaignTitle = camp.data.title;
  router.setRouteTitle('campaign:' + camp.data.id, camp.data.title);
  host.campaignMembers = members.data;
  host.campaignSessions = sessions.data;
  host.characters = chars.data;
  host.rosterCampaigns = rosterCamps.data;
  const view = host.getActiveView();
  if (view === 'campaign-codex') await loadCodexData(host, c);
  else if (view === 'campaign-analytics') await loadAnalyticsData(host, c);
}

async function loadRoster(host: RunefobleApp): Promise<void> {
  const [chars, rosterCamps] = await Promise.all([appDataService.fetchCharacters(), appDataService.fetchRosterCampaignOptions()]);
  if (!chars.ok || !rosterCamps.ok) return failLoad(host, chars, rosterCamps);
  host.characters = chars.data;
  host.rosterCampaigns = rosterCamps.data;
}

async function loadCharacterSheet(host: RunefobleApp, route: MatchedRoute): Promise<void> {
  const charId = route.params.characterId ?? '';
  host.selectedCharacterId = charId;
  host.selectedCharacter = null;
  const res = await appDataService.fetchCharacter(charId);
  if (!res.ok) return failLoad(host, res);
  host.selectedCharacter = res.data;
  if (host.selectedCharacter?.name) {
    router.setRouteTitle('character:' + charId, host.selectedCharacter.name);
    host.breadcrumbs = router.getCurrentRoute()?.breadcrumbs || host.breadcrumbs;
  }
}
