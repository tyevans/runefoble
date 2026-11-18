/**
 * App Shell View Templates (TASK-0640b).
 *
 * Renders the routed views of the App Shell main region. The session and character
 * sheet views live in session-view-templates.ts. Event handlers call the App Shell host.
 */

import { html } from 'lit';
import { router } from '../router/index.ts';
import type { RunefobleApp, AppActiveView } from '../runefoble-app.ts';
import type { DataFailure } from '../services/data-result.ts';
import { createCampaignFromEvent } from './campaign-actions.ts';
import { renderCharacterSheet, renderSessionActive } from './session-view-templates.ts';

type CampaignTab = 'overview' | 'characters' | 'codex' | 'analytics';

/** Renders the view for the active route. A load error replaces the view. */
export function renderActiveView(app: RunefobleApp, v: AppActiveView) {
  if (app.loadError) return renderLoadError(app, app.loadError);
  if (v === 'campaigns') return renderDashboard(app);
  if (v === 'campaign-detail' || v === 'campaign-characters' || v === 'campaign-codex' || v === 'campaign-analytics') return renderCampaignHub(app, v);
  if (v === 'characters') return renderRoster(app);
  if (v === 'character-sheet') return renderCharacterSheet(app);
  if (v === 'session-lobby') return renderLobby(app);
  if (v === 'profile') return renderProfile(app);
  if (v === 'session-active') return renderSessionActive(app);
  return html`<div class="auth-fallback-view"><h2>Authentication Portal</h2><p>Log in or create a Runefoble adventurer account to continue.</p></div>`;
}

function renderLoadError(app: RunefobleApp, failure: DataFailure) {
  return html`<runefoble-data-error status=${failure.status} message=${failure.message} @retry=${() => app.reloadRouteData()}></runefoble-data-error>`;
}

function renderDashboard(app: RunefobleApp) {
  return html`<runefoble-campaign-dashboard .campaigns=${app.campaigns} user-id=${app.currentUserId} @select-campaign=${(e: CustomEvent) => router.navigate('#/campaigns/' + e.detail.campaignId)} @create-campaign=${(e: CustomEvent) => createCampaignFromEvent(app, e)}></runefoble-campaign-dashboard>`;
}

function renderRoster(app: RunefobleApp) {
  return html`<runefoble-character-roster .characters=${app.characters} .campaigns=${app.rosterCampaigns} current-user-id=${app.currentUserId} @create-character=${app.handleCreateCharacter} @assign-campaign=${app.handleAssignCampaign} @delete-character=${app.handleDeleteCharacter} @inspect-character=${app.handleInspectCharacter}></runefoble-character-roster>`;
}

function renderProfile(app: RunefobleApp) {
  return html`<runefoble-user-profile .currentTheme=${app.currentTheme} .currentColorMode=${app.currentColorMode} @theme-changed=${(e: CustomEvent) => { if (e.detail?.theme) app.currentTheme = e.detail.theme; }} @color-mode-changed=${(e: CustomEvent) => { if (e.detail?.mode) app.currentColorMode = e.detail.mode; }} @auth-logout=${() => router.navigate('#/login')}></runefoble-user-profile>`;
}

function renderLobby(app: RunefobleApp) {
  return html`<runefoble-session-lobby session-id=${app.sessionId} campaign-id=${app.campaignId} session-title=${app.sessionTitle} current-user-id=${app.currentUserId} .participants=${app.lobbyParticipants} .availableCharacters=${app.lobbyAvailableCharacters} .isDm=${app.isDM} .canLaunch=${app.isDM} @select-character=${app.handleSelectCharacter} @character-selected=${app.handleSelectCharacter} @launch-session=${app.handleLaunchSession} @toggle-readiness=${(e: CustomEvent) => app.handleToggleReadiness(e)} @toggle-stand-in=${(e: CustomEvent) => app.handleToggleStandIn(e)}></runefoble-session-lobby>`;
}

function renderCampaignHub(app: RunefobleApp, v: AppActiveView) {
  const activeTab: CampaignTab = v === 'campaign-characters' ? 'characters' : v === 'campaign-codex' ? 'codex' : v === 'campaign-analytics' ? 'analytics' : 'overview';
  const canManage = app.isDM || app.currentCampaign?.role === 'owner' || app.currentCampaign?.role === 'dm';
  return html`<div class="campaign-hub-layout">
    <runefoble-campaign-header .campaign=${app.currentCampaign} .canManage=${canManage} current-user-id=${app.currentUserId} @update-campaign=${(e: CustomEvent) => app.handleUpdateCampaign(e)}></runefoble-campaign-header>
    ${renderCampaignTabs(app, activeTab)}
    <div class="campaign-tab-content">${renderCampaignTabContent(app, activeTab, canManage)}</div>
  </div>`;
}

function renderCampaignTabContent(app: RunefobleApp, activeTab: CampaignTab, canManage: boolean) {
  if (activeTab === 'overview') {
    return html`<div class="campaign-detail-layout">
      <runefoble-campaign-members campaign-id=${app.campaignId} campaign-title=${app.campaignTitle} .members=${app.campaignMembers} .canManage=${canManage} .isGm=${canManage} current-user-id=${app.currentUserId} .inviteUrl=${app.inviteUrl} .inviteToken=${app.inviteToken} @assign-role=${(e: CustomEvent) => app.handleAssignRole(e)} @create-invite=${(e: CustomEvent) => app.handleCreateInvite(e)} @remove-member=${(e: CustomEvent) => app.handleRemoveMember(e)}></runefoble-campaign-members>
      <runefoble-session-list campaign-id=${app.campaignId} .sessions=${app.campaignSessions} .isDm=${app.isDM} @enter-lobby=${(e: CustomEvent) => router.navigate('#/campaigns/' + app.campaignId + '/lobby/' + e.detail.sessionId)} @join-session=${(e: CustomEvent) => router.navigate('#/campaigns/' + app.campaignId + '/sessions/' + e.detail.sessionId)} @create-session=${(e: CustomEvent) => app.handleCreateSession(e)}></runefoble-session-list>
    </div>`;
  }
  if (activeTab === 'characters') {
    return html`<runefoble-character-roster campaign-id=${app.campaignId} .characters=${app.characters.filter((c) => c.campaignId === app.campaignId)} .campaigns=${app.rosterCampaigns} current-user-id=${app.currentUserId} active-filter="assigned" @create-character=${app.handleCreateCharacter} @assign-campaign=${app.handleAssignCampaign} @delete-character=${app.handleDeleteCharacter} @inspect-character=${app.handleInspectCharacter}></runefoble-character-roster>`;
  }
  if (activeTab === 'codex') return renderCodexTab(app);
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
      ? html`<runefoble-campaign-atlas .campaignId=${app.campaignId} .pins=${app.campaignAtlas?.pins ?? []} .territories=${app.campaignAtlas?.territories ?? []} .isDM=${app.isDM}></runefoble-campaign-atlas>`
      : html`<runefoble-campaign-codex .campaignId=${app.campaignId} .entries=${app.campaignLoreEntries} .isDM=${app.isDM}></runefoble-campaign-codex>`}`;
}

function renderCampaignTabs(app: RunefobleApp, activeTab: CampaignTab) {
  const cId = app.campaignId;
  return html`<nav class="campaign-nav-tabs" role="tablist" aria-label="Campaign Sections"><a class="nav-tab ${activeTab === 'overview' ? 'active' : ''}" role="tab" aria-selected=${activeTab === 'overview'} href="#/campaigns/${cId}" @click=${(e: Event) => { e.preventDefault(); router.navigate('#/campaigns/' + cId); }}>Overview & Sessions</a><a class="nav-tab ${activeTab === 'characters' ? 'active' : ''}" role="tab" aria-selected=${activeTab === 'characters'} href="#/campaigns/${cId}/characters" @click=${(e: Event) => { e.preventDefault(); router.navigate('#/campaigns/' + cId + '/characters'); }}>Party Characters</a><a class="nav-tab ${activeTab === 'codex' ? 'active' : ''}" role="tab" aria-selected=${activeTab === 'codex'} href="#/campaigns/${cId}/codex" @click=${(e: Event) => { e.preventDefault(); router.navigate('#/campaigns/' + cId + '/codex'); }}>Codex & Lore</a><a class="nav-tab ${activeTab === 'analytics' ? 'active' : ''}" role="tab" aria-selected=${activeTab === 'analytics'} href="#/campaigns/${cId}/analytics" @click=${(e: Event) => { e.preventDefault(); router.navigate('#/campaigns/' + cId + '/analytics'); }}>Chronicle & Stats</a></nav>`;
}
