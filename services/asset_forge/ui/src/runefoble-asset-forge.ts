import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { assetForgeStyles } from './runefoble-asset-forge.styles.ts';

export interface ForgedMapData {
  asset_id: string;
  image_url: string;
  theme: string;
  width_cells: number;
  height_cells: number;
  wall_count: number;
  hazard_count: number;
}

export interface ForgedTokenData {
  asset_id: string;
  image_url: string;
  token_name: string;
  token_type: string;
  size_px: number;
}

@customElement('runefoble-asset-forge')
export class RunefobleAssetForge extends LitElement {
  static styles = assetForgeStyles;

  @property({ type: String })
  campaignId = '';

  @property({ type: String })
  activeTab: 'battlemap' | 'token' = 'battlemap';

  @property({ type: Boolean })
  isGenerating = false;

  @property({ type: Object })
  lastForgedMap: ForgedMapData | null = null;

  @property({ type: Object })
  lastForgedToken: ForgedTokenData | null = null;

  @state()
  private mapPrompt = 'Subterranean dwarven forge with lava canals and broken anvil statues';

  @state()
  private tokenPrompt = 'Dwarven paladin with glowing runic hammer';

  @state()
  private tokenName = 'Thorin Ironbreaker';

  @state()
  private tokenType = 'pc';

  private handleForgeMap() {
    this.dispatchEvent(
      new CustomEvent('forge-battlemap', {
        detail: {
          prompt: this.mapPrompt,
          campaignId: this.campaignId,
          width_cells: 20,
          height_cells: 20,
        },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleForgeToken() {
    this.dispatchEvent(
      new CustomEvent('forge-token', {
        detail: {
          prompt: this.tokenPrompt,
          token_name: this.tokenName,
          token_type: this.tokenType,
          campaignId: this.campaignId,
        },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleProjectGeometry() {
    this.dispatchEvent(
      new CustomEvent('geometry-projected', {
        detail: { map: this.lastForgedMap },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handlePlaceToken() {
    this.dispatchEvent(
      new CustomEvent('token-placed', {
        detail: { token: this.lastForgedToken },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    return html`
      <div class="header">
        <span class="title">Tactical Asset Forge</span>
        <span style="font-size: 0.75rem; font-weight: 700;">Procedural Diffusion Engine</span>
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
                src=${this.lastForgedMap.image_url}
                alt="Forged Battlemap Preview"
              />
              <div class="stats-row">
                <span class="stat-badge">Theme: ${this.lastForgedMap.theme}</span>
                <span class="stat-badge">${this.lastForgedMap.width_cells}x${this.lastForgedMap.height_cells} Grid</span>
                <span class="stat-badge">${this.lastForgedMap.wall_count} Walls</span>
                <span class="stat-badge">${this.lastForgedMap.hazard_count} Hazards</span>
              </div>
              <button class="action-btn" @click=${this.handleProjectGeometry}>
                Project Geometry to Board State
              </button>
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
                src=${this.lastForgedToken.image_url}
                alt="Forged Token Preview"
                style="width: 120px; height: 120px; border-radius: 50%; border: 3px solid #e63946; background: transparent;"
              />
              <div class="stats-row" style="justify-content: center;">
                <span class="stat-badge">${this.lastForgedToken.token_type.toUpperCase()}</span>
                <span class="stat-badge">Circular Mask</span>
                <span class="stat-badge">Alpha Transparent</span>
              </div>
              <button class="action-btn" @click=${this.handlePlaceToken}>
                Place Token on Tactical Board
              </button>
            </div>
          `
        : ''}
    `;
  }
}
