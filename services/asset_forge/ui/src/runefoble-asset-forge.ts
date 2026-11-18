import { AuthConsumerController, fetchAssetObjectUrl, revokeAssetObjectUrl } from '@runefoble/ui-core';
import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { assetForgeStyles } from './runefoble-asset-forge.styles.ts';
import {
  forgeBattlemap,
  forgeToken,
  placeBoardToken,
  type ForgedMapData,
  type ForgedTokenData,
} from './forge-api.ts';

@customElement('runefoble-asset-forge')
export class RunefobleAssetForge extends LitElement {
  static styles = assetForgeStyles;

  private readonly auth = new AuthConsumerController(this);

  @property({ type: String })
  campaignId = '';

  /** Base URL prepended to the forge routes (for example, the gateway origin). */
  @property({ type: String })
  apiBaseUrl = '';

  /** Board session that receives a placed token. Required before placement. */
  @property({ type: String })
  sessionId = '';

  @property({ type: String })
  activeTab: 'battlemap' | 'token' = 'battlemap';

  @property({ type: Boolean })
  isGenerating = false;

  @property({ type: Object })
  lastForgedMap: ForgedMapData | null = null;

  @property({ type: Object })
  lastForgedToken: ForgedTokenData | null = null;

  /** Blob URLs for the previews (TASK-0785). Forged bytes need a bearer, so `<img src>` cannot load them. */
  @property({ type: String })
  mapPreviewUrl = '';

  @property({ type: String })
  tokenPreviewUrl = '';

  @state()
  private mapPrompt = 'Subterranean dwarven forge with lava canals and broken anvil statues';

  @state()
  private tokenPrompt = 'Dwarven paladin with glowing runic hammer';

  @state()
  private tokenName = 'Thorin Ironbreaker';

  @state()
  private tokenType = 'pc';

  @state()
  private tokenX = 0;

  @state()
  private tokenY = 0;

  @state()
  private errorMessage = '';

  disconnectedCallback() {
    super.disconnectedCallback();
    revokeAssetObjectUrl(this.mapPreviewUrl);
    revokeAssetObjectUrl(this.tokenPreviewUrl);
  }

  /** Runs one forge request. Shows the error on failure. Never reports false success. */
  private async runForge(action: () => Promise<void>) {
    this.isGenerating = true;
    this.errorMessage = '';
    try {
      await action();
    } catch (err) {
      this.errorMessage = err instanceof Error ? err.message : 'Forge request failed.';
    } finally {
      this.isGenerating = false;
    }
  }

  private async handleForgeMap() {
    await this.runForge(async () => {
      const map = await forgeBattlemap(this.apiBaseUrl, {
        prompt: this.mapPrompt,
        campaignId: this.campaignId || undefined,
        widthCells: 20,
        heightCells: 20,
      });
      const preview = await fetchAssetObjectUrl(map.image_url, () => this.auth.authHeaders());
      revokeAssetObjectUrl(this.mapPreviewUrl);
      this.mapPreviewUrl = preview;
      this.lastForgedMap = map;
      this.dispatchEvent(
        new CustomEvent('forge-battlemap', {
          detail: {
            prompt: this.mapPrompt,
            campaignId: this.campaignId,
            width_cells: 20,
            height_cells: 20,
            asset: map,
          },
          bubbles: true,
          composed: true,
        })
      );
    });
  }

  private async handleForgeToken() {
    await this.runForge(async () => {
      const token = await forgeToken(this.apiBaseUrl, {
        prompt: this.tokenPrompt,
        tokenName: this.tokenName,
        tokenType: this.tokenType,
        campaignId: this.campaignId || undefined,
      });
      const preview = await fetchAssetObjectUrl(token.image_url, () => this.auth.authHeaders());
      revokeAssetObjectUrl(this.tokenPreviewUrl);
      this.tokenPreviewUrl = preview;
      this.lastForgedToken = token;
      this.dispatchEvent(
        new CustomEvent('forge-token', {
          detail: {
            prompt: this.tokenPrompt,
            token_name: this.tokenName,
            token_type: this.tokenType,
            campaignId: this.campaignId,
            asset: token,
          },
          bubbles: true,
          composed: true,
        })
      );
    });
  }

  private async handlePlaceToken() {
    await this.runForge(async () => {
      if (!this.sessionId) {
        throw new Error('Set a session ID before placing a token.');
      }
      const forged = this.lastForgedToken;
      if (!forged) {
        throw new Error('Forge a token before placing it.');
      }
      const placed = await placeBoardToken(this.apiBaseUrl, {
        sessionId: this.sessionId,
        name: forged.token_name,
        tokenType: forged.token_type,
        x: this.tokenX,
        y: this.tokenY,
      });
      this.dispatchEvent(
        new CustomEvent('token-placed', {
          detail: {
            session_id: this.sessionId,
            token: placed,
            asset: forged,
          },
          bubbles: true,
          composed: true,
        })
      );
    });
  }

  render() {
    return html`
      <div class="header">
        <span class="title">Tactical Asset Forge</span>
        <span style="font-size: 0.75rem; font-weight: 700;">Procedural Battlemap Forge</span>
      </div>

      <div class="tabs">
        <button
          class="tab-btn ${this.activeTab === 'battlemap' ? 'active' : ''}"
          @click=${() => (this.activeTab = 'battlemap')}
        >
          Procedural Battlemap
        </button>
        <button
          class="tab-btn ${this.activeTab === 'token' ? 'active' : ''}"
          @click=${() => (this.activeTab = 'token')}
        >
          Token Portrait
        </button>
      </div>

      ${this.activeTab === 'battlemap' ? this.renderBattlemapTab() : this.renderTokenTab()}
      ${this.errorMessage
        ? html`<div class="error-banner" role="alert">${this.errorMessage}</div>`
        : ''}
    `;
  }

  private renderBattlemapTab() {
    return html`
      <div class="form-group">
        <label class="form-label">Battlemap Prompt</label>
        <input
          type="text"
          class="input-field"
          .value=${this.mapPrompt}
          @input=${(e: Event) => (this.mapPrompt = (e.target as HTMLInputElement).value)}
          placeholder="e.g. Subterranean dwarven forge with lava canals"
        />
      </div>

      <button
        class="submit-btn"
        ?disabled=${this.isGenerating}
        @click=${this.handleForgeMap}
      >
        ${this.isGenerating ? 'Synthesizing Map...' : 'Forge Tactical Battlemap'}
      </button>

      ${this.lastForgedMap
        ? html`
            <div class="preview-card">
              <div style="font-weight: 700; font-size: 0.85rem;">Forged Battlemap Ready</div>
              <img
                class="preview-image"
                src=${this.mapPreviewUrl}
                alt="Forged Battlemap Preview"
              />
              <div class="stats-row">
                <span class="stat-badge">Theme: ${this.lastForgedMap.theme}</span>
                <span class="stat-badge">${this.lastForgedMap.width_cells}x${this.lastForgedMap.height_cells} Grid</span>
                <span class="stat-badge">${this.lastForgedMap.wall_count} Walls</span>
                <span class="stat-badge">${this.lastForgedMap.hazard_count} Hazards</span>
              </div>
            </div>
          `
        : ''}
    `;
  }

  private renderTokenTab() {
    return html`
      <div class="form-group">
        <label class="form-label">Token Name</label>
        <input
          type="text"
          class="input-field"
          .value=${this.tokenName}
          @input=${(e: Event) => (this.tokenName = (e.target as HTMLInputElement).value)}
        />
      </div>

      <div class="row">
        <div class="form-group" style="flex: 1;">
          <label class="form-label">Token Type</label>
          <select
            class="input-field"
            .value=${this.tokenType}
            @change=${(e: Event) => (this.tokenType = (e.target as HTMLSelectElement).value)}
          >
            <option value="pc">Player Character</option>
            <option value="npc">NPC</option>
            <option value="monster">Monster</option>
          </select>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">Visual Description</label>
        <input
          type="text"
          class="input-field"
          .value=${this.tokenPrompt}
          @input=${(e: Event) => (this.tokenPrompt = (e.target as HTMLInputElement).value)}
          placeholder="e.g. Glowing runic armor, heavy maul"
        />
      </div>

      <button
        class="submit-btn"
        ?disabled=${this.isGenerating}
        @click=${this.handleForgeToken}
      >
        ${this.isGenerating ? 'Synthesizing Portrait...' : 'Forge Token Portrait'}
      </button>

      ${this.lastForgedToken
        ? html`
            <div class="preview-card" style="align-items: center; text-align: center;">
              <div style="font-weight: 700; font-size: 0.85rem;">${this.lastForgedToken.token_name}</div>
              <img
                src=${this.tokenPreviewUrl}
                alt="Forged Token Preview"
                style="width: 120px; height: 120px; border-radius: 50%; border: 3px solid #e63946; background: transparent;"
              />
              <div class="stats-row" style="justify-content: center;">
                <span class="stat-badge">${this.lastForgedToken.token_type.toUpperCase()}</span>
                <span class="stat-badge">Circular Mask</span>
                <span class="stat-badge">Alpha Transparent</span>
              </div>
              <div class="row">
                <div class="form-group" style="flex: 1;">
                  <label class="form-label">Column (x)</label>
                  <input
                    type="number"
                    class="input-field"
                    min="0"
                    .value=${String(this.tokenX)}
                    @input=${(e: Event) => (this.tokenX = Number((e.target as HTMLInputElement).value))}
                  />
                </div>
                <div class="form-group" style="flex: 1;">
                  <label class="form-label">Row (y)</label>
                  <input
                    type="number"
                    class="input-field"
                    min="0"
                    .value=${String(this.tokenY)}
                    @input=${(e: Event) => (this.tokenY = Number((e.target as HTMLInputElement).value))}
                  />
                </div>
              </div>
              <button class="action-btn" ?disabled=${this.isGenerating} @click=${this.handlePlaceToken}>
                Place Token on Tactical Board
              </button>
            </div>
          `
        : ''}
    `;
  }
}
