/**
 * The join view for `#/join/<token>` (ADR-0023, TASK-0950).
 *
 * The App Shell mounts `<runefoble-campaign-join>` from the game_session bundle and passes the
 * phase. The handlers run the account request, the join, and the sign-in modal.
 */

import { html, type TemplateResult } from 'lit';
import { authService } from '../auth/auth-service.ts';
import type { RunefobleApp } from '../runefoble-app.ts';
import {
  joinCampaignFromView,
  joinStateFor,
  requestInviteAccount,
  resolveJoinPhase,
} from '../app/campaign-join-actions.ts';

export function renderCampaignJoin(app: RunefobleApp): TemplateResult {
  const token = app.routeParams.token ?? '';
  const state = joinStateFor(app, token);
  const phase = resolveJoinPhase(state, authService.isAuthenticated());
  return html`<runefoble-campaign-join
    .inviteToken=${token}
    .phase=${phase}
    .message=${state.message}
    campaign-id=${state.campaignId}
    member-role=${state.memberRole}
    @account-requested=${(e: CustomEvent) => { void requestInviteAccount(app, e.detail); }}
    @join-requested=${(e: CustomEvent) => { void joinCampaignFromView(app, e.detail.inviteToken); }}
    @sign-in-requested=${() => { app.isAuthModalOpen = true; }}
  ></runefoble-campaign-join>`;
}
