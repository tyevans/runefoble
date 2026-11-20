/**
 * The join view of an invite link (ADR-0023, TASK-0950). A presentational element.
 *
 * The App Shell chooses the phase and handles the events. The element holds only the form values.
 * The invite token is a property. It is never shown, logged, or put in an error text.
 */

import { LitElement, html, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { campaignJoinStyles } from './runefoble-campaign-join.styles.ts';
import type {
  CampaignJoinPhase,
  CreateInviteAccountEventDetail,
  JoinCampaignEventDetail,
} from './types.ts';

@customElement('runefoble-campaign-join')
export class RunefobleCampaignJoin extends LitElement {
  static styles = campaignJoinStyles;

  @property({ type: String, attribute: 'invite-token' }) inviteToken = '';
  @property({ type: String }) phase: CampaignJoinPhase = 'account-form';
  /** The refusal text from the server, or an empty string. */
  @property({ type: String }) message = '';
  @property({ type: String, attribute: 'campaign-id' }) campaignId = '';
  @property({ type: String, attribute: 'member-role' }) memberRole = '';

  @state() private displayName = '';
  @state() private email = '';

  private emit<T>(name: string, detail: T): void {
    this.dispatchEvent(new CustomEvent<T>(name, { detail, bubbles: true, composed: true }));
  }

  private handleAccountSubmit(e: Event): void {
    e.preventDefault();
    const detail: CreateInviteAccountEventDetail = {
      inviteToken: this.inviteToken,
      email: this.email.trim(),
      displayName: this.displayName.trim(),
    };
    this.emit('account-requested', detail);
  }

  private requestJoin(): void {
    const detail: JoinCampaignEventDetail = { inviteToken: this.inviteToken };
    this.emit('join-requested', detail);
  }

  private requestSignIn(): void {
    this.emit('sign-in-requested', {});
  }

  private renderAlert() {
    if (!this.message) return nothing;
    return html`<p class="join-alert" role="alert">${this.message}</p>`;
  }

  private renderAccountForm(sending: boolean) {
    return html`
      <form class="join-form" @submit=${this.handleAccountSubmit}>
        <label class="join-label">
          Display name
          <input class="join-input" name="displayName" type="text" required maxlength="100" autocomplete="nickname"
            .value=${this.displayName} ?disabled=${sending}
            @input=${(e: Event) => { this.displayName = (e.target as HTMLInputElement).value; }} />
        </label>
        <label class="join-label">
          E-mail address
          <input class="join-input" name="email" type="email" required maxlength="254" autocomplete="email"
            .value=${this.email} ?disabled=${sending}
            @input=${(e: Event) => { this.email = (e.target as HTMLInputElement).value; }} />
        </label>
        <div class="join-actions">
          <button class="join-button" type="submit" ?disabled=${sending}>${sending ? 'Creating account...' : 'Create account'}</button>
          <button class="join-button-secondary" type="button" @click=${this.requestSignIn}>I already have an account</button>
        </div>
      </form>
    `;
  }

  private renderBody() {
    switch (this.phase) {
      case 'account-form':
        return html`
          <p class="join-text">An invite lets you create a Runefoble account. Enter a display name and your e-mail address.</p>
          ${this.renderAccountForm(false)}`;
      case 'account-sending':
        return html`
          <p class="join-text">Creating your account. Please wait.</p>
          ${this.renderAccountForm(true)}`;
      case 'account-refused':
        return html`
          ${this.renderAlert()}
          ${this.renderAccountForm(false)}`;
      case 'account-accepted':
        return html`
          <p class="join-text">Zitadel sent a message to your e-mail address. Open that message, set a password, then sign in here.</p>
          <div class="join-actions">
            <button class="join-button" type="button" @click=${this.requestSignIn}>Sign in</button>
          </div>`;
      case 'join-ready':
        return html`
          <p class="join-text">You hold a valid invite. Join this campaign with your account.</p>
          <div class="join-actions">
            <button class="join-button" type="button" @click=${this.requestJoin}>Join campaign</button>
          </div>`;
      case 'joining':
        return html`
          <p class="join-text">Joining the campaign.</p>
          <div class="join-actions">
            <button class="join-button" type="button" disabled>Joining...</button>
          </div>`;
      case 'joined':
        return html`
          <p class="join-text">You joined this campaign as ${this.memberRole || 'a member'}.</p>
          <div class="join-actions">
            <a class="join-link" href=${`#/campaigns/${this.campaignId}`}>Open campaign</a>
          </div>`;
      case 'join-refused':
        return html`
          ${this.renderAlert()}
          <div class="join-actions">
            <button class="join-button" type="button" @click=${this.requestJoin}>Try again</button>
          </div>`;
    }
  }

  private titleFor(phase: CampaignJoinPhase): string {
    switch (phase) {
      case 'account-form':
      case 'account-sending':
      case 'account-refused':
        return 'Join the Campaign';
      case 'account-accepted':
        return 'Check Your E-mail';
      case 'join-ready':
      case 'joining':
        return 'You Are Invited';
      case 'joined':
        return 'Joined';
      case 'join-refused':
        return 'Invite Not Joined';
    }
  }

  render() {
    // A link without a token has nothing to show. The element shows no text for it.
    if (!this.inviteToken) return nothing;
    return html`
      <section class="join-card" data-phase=${this.phase}>
        <h2 class="join-title">${this.titleFor(this.phase)}</h2>
        ${this.renderBody()}
      </section>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-campaign-join': RunefobleCampaignJoin;
  }
}
