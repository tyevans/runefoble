/**
 * Campaign Hub View (TASK-0643). Renders the campaign header, the section tabs, and the active tab.
 * Loads the campaign, members, sessions, roster, and the codex or analytics data for the tab.
 */

import { html } from 'lit';
import { router } from '../router/index.ts';
import type { RunefobleApp } from '../runefoble-app.ts';
import type { AppActiveView } from '../router/view-resolver.ts';
import type { MatchedRoute } from '../router/index.ts';
import { appDataService } from '../services/app-data-service.ts';
import { failLoad } from '../app/load-error.ts';
import { loadAnalyticsData, loadCodexData } from '../app/campaign-hub-data-loader.ts';
import { assignRoleFromEvent, createInviteFromEvent, removeMemberFromEvent, createSessionFromEvent, updateCampaignFromEvent } from '../app/campaign-actions.ts';
import { assignCharacterFromEvent, createCharacterFromEvent, deleteCharacterFromEvent } from '../app/character-actions.ts';
import { createEntryFromEvent, createPinFromEvent } from '../app/lore-actions.ts';
import { inspectCharacterFromEvent } from './character-view.ts';
import { setCurrentCampaign } from '../app/shell-state.ts';
import { resolveForgeAccess } from './forge-access.ts';

type CampaignTab = 'overview' | 'characters' | 'codex' | 'analytics' | 'forge';

/**
 * Base URL for the forge routes. The App Shell is served behind the gateway origin, so the
 * forge elements call the same-origin `/api/v1/forge/*` routes through the gateway.
 */
const FORGE_API_BASE_URL = '';

export async function loadCampaignHubData(host: RunefobleApp, route: MatchedRoute): Promise<void> {
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
  setCurrentCampaign(host, camp.data);
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

export function renderCampaignHub(app: RunefobleApp, v: AppActiveView) {
  const activeTab: CampaignTab = v === 'campaign-characters' ? 'characters' : v === 'campaign-codex' ? 'codex' : v === 'campaign-analytics' ? 'analytics' : v === 'campaign-forge' ? 'forge' : 'overview';
  const permissions = app.currentCampaign?.permissions;
  const canManage = Boolean(permissions?.manage);
  const canForge = resolveForgeAccess(permissions) === 'allowed';
  return html`<div class="campaign-hub-layout">
    <runefoble-campaign-header .campaign=${app.currentCampaign} .canManage=${canManage} current-user-id=${app.currentUserId} @update-campaign=${(e: CustomEvent) => updateCampaignFromEvent(app, e)}></runefoble-campaign-header>
    ${renderCampaignTabs(app, activeTab, canForge)}
    <div class="campaign-tab-content">${renderCampaignTabContent(app, activeTab, canManage, canForge)}</div>
  </div>`;
}

function renderCampaignTabContent(app: RunefobleApp, activeTab: CampaignTab, canManage: boolean, canForge: boolean) {
  if (activeTab === 'overview') {
    return html`<div class="campaign-detail-layout">
      <runefoble-campaign-members campaign-id=${app.campaignId} campaign-title=${app.campaignTitle} .members=${app.campaignMembers} .canManage=${canManage} .isGm=${canManage} current-user-id=${app.currentUserId} .inviteUrl=${app.inviteUrl} .inviteToken=${app.inviteToken} @assign-role=${(e: CustomEvent) => assignRoleFromEvent(app, e)} @create-invite=${(e: CustomEvent) => createInviteFromEvent(app, e)} @remove-member=${(e: CustomEvent) => removeMemberFromEvent(app, e)}></runefoble-campaign-members>
      <runefoble-session-list campaign-id=${app.campaignId} .sessions=${app.campaignSessions} .isDm=${Boolean(app.currentCampaign?.permissions.launch_session)} @enter-lobby=${(e: CustomEvent) => router.navigate('#/campaigns/' + app.campaignId + '/lobby/' + e.detail.sessionId)} @join-session=${(e: CustomEvent) => router.navigate('#/campaigns/' + app.campaignId + '/sessions/' + e.detail.sessionId)} @create-session=${(e: CustomEvent) => createSessionFromEvent(app, e)}></runefoble-session-list>
    </div>`;
  }
  if (activeTab === 'characters') {
    return html`<runefoble-character-roster campaign-id=${app.campaignId} .characters=${app.characters.filter((c) => c.campaignId === app.campaignId)} .campaigns=${app.rosterCampaigns} current-user-id=${app.currentUserId} active-filter="assigned" @create-character=${(e: CustomEvent) => createCharacterFromEvent(app, e)} @assign-campaign=${(e: CustomEvent) => assignCharacterFromEvent(app, e)} @delete-character=${(e: CustomEvent) => deleteCharacterFromEvent(app, e)} @inspect-character=${(e: CustomEvent) => inspectCharacterFromEvent(e)}></runefoble-character-roster>`;
  }
  if (activeTab === 'codex') return renderCodexTab(app);
  if (activeTab === 'forge') {
    if (!canForge) {
      return html`<div class="forge-not-permitted" role="alert"><h2>Asset Forge Not Permitted</h2><p>Only a campaign manager can use the Asset Forge in this campaign.</p></div>`;
    }
    return html`<div class="campaign-forge-layout">
      <runefoble-asset-forge campaign-id=${app.campaignId} .apiBaseUrl=${FORGE_API_BASE_URL}></runefoble-asset-forge>
      <runefoble-print-forge campaign-id=${app.campaignId} .apiBaseUrl=${FORGE_API_BASE_URL}></runefoble-print-forge>
    </div>`;
  }
  return html`<runefoble-campaign-analytics .campaignId=${app.campaignId} .heatmapData=${app.campaignAnalytics?.heatmap ?? null} .mvpData=${app.campaignAnalytics?.mvp ?? null} .timelineData=${app.campaignAnalytics?.timeline ?? null}></runefoble-campaign-analytics>`;
}

/** Codex & Lore tab. Two sub-tabs mount the atlas and the lore codex with live data. */
function renderCodexTab(app: RunefobleApp) {
  const view = app.campaignCodexView;
  const selectView = (next: 'atlas' | 'codex') => { app.campaignCodexView = next; };
  return html`<div class="codex-subtabs" role="tablist" aria-label="Codex Views">
      <button class="nav-tab ${view === 'atlas' ? 'active' : ''}" role="tab" aria-selected=${view === 'atlas'} @click=${() => selectView('atlas')}>World Atlas</button>
      <button class="nav-tab ${view === 'codex' ? 'active' : ''}" role="tab" aria-selected=${view === 'codex'} @click=${() => selectView('codex')}>Lore Codex</button>
    </div>
    ${view === 'atlas'
      ? html`<runefoble-campaign-atlas .campaignId=${app.campaignId} .pins=${app.campaignAtlas?.pins ?? []} .territories=${app.campaignAtlas?.territories ?? []} .isDM=${Boolean(app.currentCampaign?.permissions.launch_session)} .pinError=${app.campaignPinError ?? ''} @pin-create-requested=${(e: CustomEvent) => createPinFromEvent(app, e)}></runefoble-campaign-atlas>`
      : html`<runefoble-campaign-codex .campaignId=${app.campaignId} .entries=${app.campaignLoreEntries} .isDM=${Boolean(app.currentCampaign?.permissions.launch_session)} .entryError=${app.campaignEntryError ?? ''} @codex-entry-create-requested=${(e: CustomEvent) => createEntryFromEvent(app, e)}></runefoble-campaign-codex>`}`;
}

function renderCampaignTabs(app: RunefobleApp, activeTab: CampaignTab, canForge: boolean) {
  const cId = app.campaignId;
  return html`<nav class="campaign-nav-tabs" role="tablist" aria-label="Campaign Sections"><a class="nav-tab ${activeTab === 'overview' ? 'active' : ''}" role="tab" aria-selected=${activeTab === 'overview'} href="#/campaigns/${cId}" @click=${(e: Event) => { e.preventDefault(); router.navigate('#/campaigns/' + cId); }}>Overview & Sessions</a><a class="nav-tab ${activeTab === 'characters' ? 'active' : ''}" role="tab" aria-selected=${activeTab === 'characters'} href="#/campaigns/${cId}/characters" @click=${(e: Event) => { e.preventDefault(); router.navigate('#/campaigns/' + cId + '/characters'); }}>Party Characters</a><a class="nav-tab ${activeTab === 'codex' ? 'active' : ''}" role="tab" aria-selected=${activeTab === 'codex'} href="#/campaigns/${cId}/codex" @click=${(e: Event) => { e.preventDefault(); router.navigate('#/campaigns/' + cId + '/codex'); }}>Codex & Lore</a><a class="nav-tab ${activeTab === 'analytics' ? 'active' : ''}" role="tab" aria-selected=${activeTab === 'analytics'} href="#/campaigns/${cId}/analytics" @click=${(e: Event) => { e.preventDefault(); router.navigate('#/campaigns/' + cId + '/analytics'); }}>Chronicle & Stats</a>${canForge ? html`<a class="nav-tab ${activeTab === 'forge' ? 'active' : ''}" role="tab" aria-selected=${activeTab === 'forge'} href="#/campaigns/${cId}/forge" @click=${(e: Event) => { e.preventDefault(); router.navigate('#/campaigns/' + cId + '/forge'); }}>Asset Forge</a>` : ''}</nav>`;
}
