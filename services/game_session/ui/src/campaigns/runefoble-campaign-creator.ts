import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { campaignCreatorStyles } from './runefoble-campaign-creator.styles.ts';
import type { CreateCampaignPayload } from './types.ts';

@customElement('runefoble-campaign-creator')
export class RunefobleCampaignCreator extends LitElement {
  static styles = [campaignCreatorStyles];

  @property({ type: Boolean, reflect: true }) open = false;
  @property({ type: String }) title = '';
  @property({ type: String }) setting = '';
  @property({ type: String }) system = '5e';
  @property({ type: String, attribute: 'cover-image-url' }) coverImageUrl = '';
  @property({ type: String }) description = '';
  @property({ type: Boolean }) submitting = false;
  @property({ type: String }) errorMessage = '';

  @state() private internalError = '';

  public openModal(): void {
    this.open = true;
    this.internalError = '';
  }

  public closeModal(): void {
    this.open = false;
    this.internalError = '';
    this.dispatchEvent(new CustomEvent('close', { bubbles: true, composed: true }));
    this.dispatchEvent(new CustomEvent('cancel', { bubbles: true, composed: true }));
  }

  public reset(): void {
    this.title = '';
    this.setting = '';
    this.system = '5e';
    this.coverImageUrl = '';
    this.description = '';
    this.internalError = '';
    this.errorMessage = '';
    this.submitting = false;
  }

  private handleBackdropClick(e: MouseEvent): void {
    if (e.target === e.currentTarget) {
      this.closeModal();
    }
  }

  private handleSubmit(e: Event): void {
    e.preventDefault();
    const trimmedTitle = this.title.trim();
    if (!trimmedTitle) {
      this.internalError = 'Campaign title is required.';
      return;
    }

    const payload: CreateCampaignPayload = {
      title: trimmedTitle,
      setting: this.setting.trim(),
      system: this.system || '5e',
      cover_image_url: this.coverImageUrl.trim() || undefined,
      description: this.description.trim() || undefined,
    };

    this.dispatchEvent(
      new CustomEvent<CreateCampaignPayload>('create-campaign', {
        detail: payload,
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    if (!this.open) {
      return html``;
    }

    const activeError = this.errorMessage || this.internalError;

    return html`
      <div class="modal-backdrop" @click=${this.handleBackdropClick} role="dialog" aria-modal="true" aria-labelledby="creator-title">
        <div class="modal-card">
          <div class="modal-header">
            <h2 class="modal-title" id="creator-title">Create New Campaign</h2>
            <button
              class="btn-close"
              @click=${this.closeModal}
              aria-label="Close dialog"
              type="button"
            >✕</button>
          </div>

          ${activeError
            ? html`<div class="error-banner" role="alert">⚠️ ${activeError}</div>`
            : ''}

          <form @submit=${this.handleSubmit}>
            <div class="form-group">
              <label class="form-label" for="campaign-title">
                Campaign Title <span class="required-star">*</span>
              </label>
              <input
                id="campaign-title"
                name="title"
                class="form-input"
                type="text"
                placeholder="e.g. Shadows of Drakkenheim"
                .value=${this.title}
                @input=${(e: Event) => {
                  this.title = (e.target as HTMLInputElement).value;
                  this.internalError = '';
                }}
                required
                maxlength="100"
              />
            </div>

            <div class="form-group">
              <label class="form-label" for="campaign-setting">
                Setting Synopsis
              </label>
              <input
                id="campaign-setting"
                name="setting"
                class="form-input"
                type="text"
                placeholder="e.g. Gothic Fantasy, Grimdark, High Magic"
                .value=${this.setting}
                @input=${(e: Event) => (this.setting = (e.target as HTMLInputElement).value)}
              />
              <span class="form-hint">Brief genre or world theme for your campaign</span>
            </div>

            <div class="form-group">
              <label class="form-label" for="campaign-ruleset">
                Ruleset System
              </label>
              <select
                id="campaign-ruleset"
                name="system"
                class="form-select"
                .value=${this.system}
                @change=${(e: Event) => (this.system = (e.target as HTMLSelectElement).value)}
              >
                <option value="5e">SRD 5e (Fifth Edition)</option>
                <option value="pf2e">Pathfinder 2e</option>
                <option value="daggerheart">Daggerheart</option>
                <option value="call_of_cthulhu">Call of Cthulhu</option>
                <option value="custom">Custom Ruleset</option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label" for="campaign-cover">
                Cover Art URL (Optional)
              </label>
              <input
                id="campaign-cover"
                name="coverImageUrl"
                class="form-input"
                type="url"
                placeholder="https://example.com/banner.png"
                .value=${this.coverImageUrl}
                @input=${(e: Event) => (this.coverImageUrl = (e.target as HTMLInputElement).value)}
              />
            </div>

            <div class="form-group">
              <label class="form-label" for="campaign-description">
                Description / Campaign Summary
              </label>
              <textarea
                id="campaign-description"
                name="description"
                class="form-textarea"
                placeholder="Write a brief pitch or introductory lore for prospective adventurers..."
                .value=${this.description}
                @input=${(e: Event) => (this.description = (e.target as HTMLTextAreaElement).value)}
              ></textarea>
            </div>

            <div class="modal-actions">
              <button
                type="button"
                class="btn-cancel"
                @click=${this.closeModal}
                ?disabled=${this.submitting}
              >
                Cancel
              </button>
              <button
                type="submit"
                class="btn-submit"
                ?disabled=${this.submitting}
              >
                ${this.submitting ? 'Creating...' : 'Create Campaign'}
              </button>
            </div>
          </form>
        </div>
      </div>
    `;
  }
}
