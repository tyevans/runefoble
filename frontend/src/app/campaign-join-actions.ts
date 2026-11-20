/**
 * App Shell Join Actions (TASK-0950, ADR-0023).
 *
 * Runs the account request and the join for the `#/join/<token>` view. The token is never
 * logged, never sent to analytics, and never copied into an error text. Account failures use
 * fixed texts, because a server validation reply can repeat the submitted values.
 */

import { router } from '../router/index.ts';
import type { RunefobleApp } from '../runefoble-app.ts';
import { appDataService } from '../services/app-data-service.ts';
import type { CampaignJoinPhase, CreateInviteAccountEventDetail } from '@runefoble/game-session-ui';

/** The state of the join view for one invite token. `idle` means no request has run yet. */
export interface JoinViewState {
  token: string;
  phase: CampaignJoinPhase | 'idle';
  message: string;
  campaignId: string;
  memberRole: string;
}

export const IDLE_JOIN_STATE: JoinViewState = { token: '', phase: 'idle', message: '', campaignId: '', memberRole: '' };

const JOIN_FALLBACK_MESSAGE = 'The invite could not be used.';

const ACCOUNT_FAILURE_MESSAGES: Record<number, string> = {
  404: 'This invite link is not valid.',
  410: 'This invite link has expired or has no uses left.',
  422: 'Enter a display name and a valid e-mail address.',
  429: 'Too many attempts. Wait a while and try again.',
  503: 'Account creation is unavailable. Try again later.',
};

/** The text for a refused account request. It depends on the status only. */
export function accountFailureMessage(status: number): string {
  return ACCOUNT_FAILURE_MESSAGES[status] ?? 'The account could not be created. Try again.';
}

/** The state that belongs to `token`. A state for another token is never shown. */
export function joinStateFor(app: Pick<RunefobleApp, 'joinState'>, token: string): JoinViewState {
  return app.joinState.token === token ? app.joinState : { ...IDLE_JOIN_STATE, token };
}

/**
 * The phase that the view shows. A signed-in person never sees the account form, and a signed-out
 * person never sees the join button (ADR-0023 e).
 */
export function resolveJoinPhase(state: JoinViewState, signedIn: boolean): CampaignJoinPhase {
  if (state.phase === 'idle') return signedIn ? 'join-ready' : 'account-form';
  if (signedIn) return state.phase.startsWith('account') ? 'join-ready' : state.phase;
  return state.phase.startsWith('account') ? state.phase : 'account-form';
}

export async function requestInviteAccount(app: RunefobleApp, detail: CreateInviteAccountEventDetail): Promise<void> {
  const token = detail.inviteToken;
  app.joinState = { token, phase: 'account-sending', message: '', campaignId: '', memberRole: '' };
  const res = await appDataService.createInviteAccount({
    inviteToken: token,
    email: detail.email,
    displayName: detail.displayName,
  });
  app.joinState = res.ok
    ? { token, phase: 'account-accepted', message: '', campaignId: '', memberRole: '' }
    : { token, phase: 'account-refused', message: accountFailureMessage(res.status), campaignId: '', memberRole: '' };
}

export async function joinCampaignFromView(app: RunefobleApp, inviteToken: string): Promise<void> {
  app.joinState = { token: inviteToken, phase: 'joining', message: '', campaignId: '', memberRole: '' };
  const res = await appDataService.joinCampaign(inviteToken);
  if (!res.ok) {
    app.joinState = { token: inviteToken, phase: 'join-refused', message: res.message || JOIN_FALLBACK_MESSAGE, campaignId: '', memberRole: '' };
    return;
  }
  app.joinState = { token: inviteToken, phase: 'joined', message: '', campaignId: res.data.campaign_id, memberRole: res.data.role };
  await router.navigate(`#/campaigns/${res.data.campaign_id}`);
}
