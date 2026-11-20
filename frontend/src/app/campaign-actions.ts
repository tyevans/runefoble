/**
 * App Shell Campaign Actions (TASK-0640b).
 *
 * Handles campaign, session, membership, and invite events from the campaign views.
 * Each failed write shows a toast with the server message and leaves state unchanged.
 */

import { router } from '../router/index.ts';
import type { RunefobleApp } from '../runefoble-app.ts';
import { appDataService } from '../services/app-data-service.ts';
import type { CreateCampaignPayload, UpdateCampaignPayload } from '@runefoble/game-session-ui';
import { failLoad } from './load-error.ts';
import { setCurrentCampaign } from './shell-state.ts';
import { loadRouteData } from './data-loader.ts';

export async function updateCampaignFromEvent(host: RunefobleApp, e: CustomEvent<UpdateCampaignPayload>): Promise<void> {
  const p = e.detail;
  const cId = p?.campaignId || host.campaignId;
  const updated = await appDataService.updateCampaign(cId, p);
  if (!updated.ok) {
    host.showToast(`Not saved. ${updated.message}`);
    return;
  }
  setCurrentCampaign(host, updated.data);
  host.campaignTitle = updated.data.title;
  router.setRouteTitle('campaign:' + updated.data.id, updated.data.title);
  await loadRouteData(host, host.currentRoute || router.getCurrentRoute()!);
}

export async function createCampaignFromEvent(host: RunefobleApp, e: CustomEvent<CreateCampaignPayload>): Promise<void> {
  const c = await appDataService.createCampaign(e.detail);
  if (!c.ok) {
    host.showToast(`Campaign not created. ${c.message}`);
    return;
  }
  const list = await appDataService.fetchCampaigns();
  if (list.ok) host.campaigns = list.data;
  else failLoad(host, list);
  router.navigate('#/campaigns/' + c.data.id);
}

export async function createSessionFromEvent(host: RunefobleApp, e: CustomEvent): Promise<void> {
  const detail = e.detail || {};
  const status = detail.status || 'lobby';
  const created = await appDataService.createCampaignSession(host.campaignId, {
    title: detail.title || ('Session #' + ((host.campaignSessions?.length || 0) + 1)),
    status,
    scheduled_at: detail.scheduledAt || detail.scheduled_at,
    description: detail.description || '',
  });
  if (!created.ok) {
    host.showToast(`Session not created. ${created.message}`);
    return;
  }
  const sessions = await appDataService.fetchCampaignSessions(host.campaignId);
  if (sessions.ok) host.campaignSessions = sessions.data;
  else host.showToast(`Session list not refreshed. ${sessions.message}`);
  if (status === 'lobby') router.navigate('#/campaigns/' + host.campaignId + '/lobby/' + created.data.id);
}

export async function assignRoleFromEvent(host: RunefobleApp, e: CustomEvent): Promise<void> {
  const { campaignId, userId, role } = e.detail || {};
  const cId = campaignId || host.campaignId;
  const res = await appDataService.assignMemberRole(cId, userId, role);
  if (!res.ok) {
    host.showToast(`Role not changed. ${res.message}`);
    return;
  }
  const members = await appDataService.fetchCampaignMembers(cId);
  if (members.ok) host.campaignMembers = members.data;
  else host.showToast(`Member list not refreshed. ${members.message}`);
  host.showToast(`Role updated to ${role}`);
}

export async function createInviteFromEvent(host: RunefobleApp, e: CustomEvent): Promise<void> {
  const { campaignId, role, expiresInHours, maxUses } = e.detail || {};
  const cId = campaignId || host.campaignId;
  const inv = await appDataService.createCampaignInvite(cId, role, expiresInHours, maxUses);
  if (!inv.ok) {
    host.showToast(`Invite not created. ${inv.message}`);
    return;
  }
  // The server returns a path such as `/#/join/<token>`. The field shows the absolute link (ADR-0015).
  host.inviteUrl = new URL(inv.data.invite_url, window.location.origin).href;
  host.showToast(`Invite created for ${role}`);
}

export async function removeMemberFromEvent(host: RunefobleApp, e: CustomEvent): Promise<void> {
  const { campaignId, userId } = e.detail || {};
  const cId = campaignId || host.campaignId;
  const res = await appDataService.removeCampaignMember(cId, userId);
  if (!res.ok) {
    host.showToast(`Member not removed. ${res.message}`);
    return;
  }
  const members = await appDataService.fetchCampaignMembers(cId);
  if (members.ok) host.campaignMembers = members.data;
  else host.showToast(`Member list not refreshed. ${members.message}`);
  host.showToast('Member removed from campaign');
}
