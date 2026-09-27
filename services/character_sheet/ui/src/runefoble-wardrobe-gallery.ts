import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

export interface WardrobeVariantItem {
  variantId: string;
  variantName: string;
  attireType: string;
  imageUrl: string;
  prompt?: string;
  createdAt?: string;
}

@customElement('runefoble-wardrobe-gallery')
export class RunefobleWardrobeGallery extends LitElement {
  static styles = css`
    :host {
      display: block;
      font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
      background: var(--rf-bg-card, #202225);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #36393f);
      border-radius: var(--rf-border-radius, 4px);
      padding: 16px;
      color: var(--rf-text-primary, #ffffff);
      max-width: 480px;
      box-shadow: var(--rf-shadow, 0 4px 12px rgba(0, 0, 0, 0.3));
      box-sizing: border-box;
    }

    .gallery-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #36393f);
      padding-bottom: 10px;
      margin-bottom: 16px;
    }

    .header-title {
      font-size: 1.1rem;
      font-weight: 800;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      color: var(--rf-text-primary, #ffffff);
    }

    .active-section {
      display: flex;
      gap: 16px;
      align-items: center;
      margin-bottom: 20px;
      background: var(--rf-bg-canvas, #18191c);
      padding: 12px;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #36393f);
      border-radius: var(--rf-border-radius, 4px);
    }

    .avatar-wrapper {
      position: relative;
      width: 96px;
      height: 96px;
      flex-shrink: 0;
    }

    .avatar-img {
      width: 100%;
      height: 100%;
      border-radius: 50%;
      object-fit: cover;
      border: 3px solid var(--rf-accent-secondary, #2a9d8f);
      box-shadow: var(--rf-shadow-sm, 0 2px 6px rgba(0, 0, 0, 0.4));
      display: block;
    }

    .avatar-img.bloodied {
      border-color: var(--rf-accent-primary, #e63946);
      box-shadow: 0 0 10px rgba(230, 57, 70, 0.6);
    }

    .avatar-img.poisoned {
      border-color: #00f5d4;
      box-shadow: 0 0 10px rgba(0, 245, 212, 0.5);
    }

    .active-info {
      flex: 1;
    }

    .character-name {
      font-size: 1.05rem;
      font-weight: 800;
      margin-bottom: 4px;
    }

    .hp-badge {
      display: inline-block;
      font-size: 0.75rem;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 2px;
      background: var(--rf-bg-card, #202225);
      border: 1px solid var(--rf-border-color, #36393f);
      margin-bottom: 8px;
    }

    .hp-badge.low {
      background: #7a1018;
      border-color: var(--rf-accent-primary, #e63946);
      color: #fff;
    }

    .condition-badges-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .badge-pill {
      font-size: 0.7rem;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 2px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }

    .badge-bloodied {
      background: var(--rf-accent-primary, #e63946);
      color: #ffffff;
    }

    .badge-poisoned {
      background: #1b8a36;
      color: #00f5d4;
      border: 1px solid #00f5d4;
    }

    .badge-stunned {
      background: #9d7b00;
      color: #ffd166;
      border: 1px solid #ffd166;
    }

    .badge-default {
      background: var(--rf-bg-card, #202225);
      border: 1px solid var(--rf-border-color, #36393f);
      color: var(--rf-text-muted, #99aab5);
    }

    .variants-title {
      font-size: 0.85rem;
      font-weight: 700;
      color: var(--rf-text-muted, #99aab5);
      text-transform: uppercase;
      margin-bottom: 8px;
    }

    .variants-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }

    .variant-card {
      background: var(--rf-bg-canvas, #18191c);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #36393f);
      border-radius: var(--rf-border-radius, 4px);
      padding: 8px;
      text-align: center;
      cursor: pointer;
      transition: border-color 0.2s ease, transform 0.1s ease;
    }

    .variant-card:hover {
      border-color: var(--rf-accent-secondary, #2a9d8f);
      transform: translateY(-2px);
    }

    .variant-card.active {
      border-color: var(--rf-accent-tertiary, #e9c46a);
      box-shadow: 0 0 6px rgba(233, 196, 106, 0.4);
    }

    .variant-thumbnail {
      width: 56px;
      height: 56px;
      border-radius: 50%;
      object-fit: cover;
      margin: 0 auto 6px auto;
      display: block;
      border: 2px solid var(--rf-border-color, #36393f);
    }

    .variant-name {
      font-size: 0.72rem;
      font-weight: 700;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      margin-bottom: 4px;
    }

    .btn-equip {
      font-size: 0.65rem;
      font-weight: 700;
      padding: 2px 6px;
      width: 100%;
      border-radius: 2px;
      background: var(--rf-accent-secondary, #2a9d8f);
      color: #ffffff;
      border: none;
      cursor: pointer;
    }

    .btn-equip.active-btn {
      background: var(--rf-accent-tertiary, #e9c46a);
      color: #121212;
    }

    .forge-panel {
      border-top: var(--rf-border-width, 2px) solid var(--rf-border-color, #36393f);
      padding-top: 12px;
      display: flex;
      gap: 8px;
      align-items: center;
    }

    .style-select {
      flex: 1;
      background: var(--rf-bg-canvas, #18191c);
      color: var(--rf-text-primary, #ffffff);
      border: 1px solid var(--rf-border-color, #36393f);
      border-radius: 2px;
      padding: 6px 8px;
      font-size: 0.8rem;
    }

    .btn-forge {
      background: var(--rf-accent-primary, #e63946);
      color: #ffffff;
      font-size: 0.8rem;
      font-weight: 800;
      border: none;
      padding: 6px 12px;
      border-radius: 2px;
      cursor: pointer;
      letter-spacing: 0.5px;
      transition: opacity 0.2s ease;
    }

    .btn-forge:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  `;

  @property({ type: String }) characterId = '';
  @property({ type: String }) characterName = 'Nadia the Bard';
  @property({ type: Number }) currentHp = 34;
  @property({ type: Number }) maxHp = 34;
  @property({ type: String }) activePortraitUrl = '/assets/portraits/default.svg';
  @property({ type: String }) basePortraitUrl = '/assets/portraits/default.svg';
  @property({ type: String }) activeVariantId: string | null = null;
  @property({ type: Array }) conditionBadges: string[] = [];
  @property({ type: Array }) variants: WardrobeVariantItem[] = [];

  @state() private selectedAttire = 'ballroom_masquerade';
  @state() private isForging = false;

  private getEffectiveBadges(): string[] {
    const list = [...this.conditionBadges];
    if (this.maxHp > 0 && this.currentHp < this.maxHp * 0.5 && !list.includes('bloodied')) {
      list.unshift('bloodied');
    }
    return list;
  }

  private handleSelectVariant(variant: WardrobeVariantItem) {
    this.activeVariantId = variant.variantId;
    this.dispatchEvent(
      new CustomEvent('portrait-selected', {
        detail: {
          variantId: variant.variantId,
          imageUrl: variant.imageUrl,
          variantName: variant.variantName,
        },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleForgeAttire() {
    this.dispatchEvent(
      new CustomEvent('generate-wardrobe', {
        detail: {
          characterId: this.characterId,
          characterName: this.characterName,
          attireType: this.selectedAttire,
        },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    const badges = this.getEffectiveBadges();
    const isBloodied = badges.includes('bloodied');
    const isPoisoned = badges.includes('poisoned');

    return html`
      <div class="gallery-header">
        <span class="header-title">Wardrobe & State Gallery</span>
        <span class="hp-badge ${isBloodied ? 'low' : ''}">
          HP: ${this.currentHp} / ${this.maxHp}
        </span>
      </div>

      <div class="active-section">
        <div class="avatar-wrapper">
          <img
            class="avatar-img ${isBloodied ? 'bloodied' : ''} ${isPoisoned ? 'poisoned' : ''}"
            src="${this.activePortraitUrl}"
            alt="${this.characterName} Active Portrait"
          />
        </div>
        <div class="active-info">
          <div class="character-name">${this.characterName}</div>
          <div class="condition-badges-row">
            ${badges.length === 0
              ? html`<span class="badge-pill badge-default">Normal / Healthy</span>`
              : badges.map((badge) => {
                  if (badge === 'bloodied') {
                    return html`<span class="badge-pill badge-bloodied">🩸 Bloodied (&lt;50% HP)</span>`;
                  }
                  if (badge === 'poisoned') {
                    return html`<span class="badge-pill badge-poisoned">🧪 Poisoned</span>`;
                  }
                  if (badge === 'stunned') {
                    return html`<span class="badge-pill badge-stunned">💫 Stunned</span>`;
                  }
                  return html`<span class="badge-pill badge-default">⚠️ ${badge}</span>`;
                })}
          </div>
        </div>
      </div>

      <div class="variants-title">Unlocked Wardrobe Variants (${this.variants.length})</div>
      <div class="variants-grid">
        ${this.variants.map((v) => {
          const isActive = this.activeVariantId === v.variantId;
          return html`
            <div
              class="variant-card ${isActive ? 'active' : ''}"
              @click=${() => this.handleSelectVariant(v)}
            >
              <img class="variant-thumbnail" src="${v.imageUrl}" alt="${v.variantName}" />
              <div class="variant-name" title="${v.variantName}">${v.variantName}</div>
              <button class="btn-equip ${isActive ? 'active-btn' : ''}">
                ${isActive ? 'Active' : 'Equip'}
              </button>
            </div>
          `;
        })}
      </div>

      <div class="forge-panel">
        <select
          class="style-select"
          .value=${this.selectedAttire}
          @change=${(e: Event) => {
            this.selectedAttire = (e.target as HTMLSelectElement).value;
          }}
        >
          <option value="ballroom_masquerade">Ballroom Masquerade</option>
          <option value="arctic_tundra">Arctic Tundra Fur</option>
          <option value="tavern_casual">Tavern Casual</option>
          <option value="battle_damaged">Battle Damaged Plate</option>
          <option value="ceremonial">Temple Ceremonial Vestment</option>
        </select>
        <button
          class="btn-forge"
          ?disabled=${this.isForging}
          @click=${this.handleForgeAttire}
        >
          ${this.isForging ? 'Synthesizing...' : 'Synthesize Attire'}
        </button>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-wardrobe-gallery': RunefobleWardrobeGallery;
  }
}
