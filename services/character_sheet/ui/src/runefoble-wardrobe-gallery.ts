import { LitElement, html, type PropertyValues } from 'lit';
import {
  AssetImageController,
  AuthConsumerController,
  PORTRAIT_PLACEHOLDERS,
} from '@runefoble/ui-core';
import { customElement, property, state } from 'lit/decorators.js';
import { wardrobeGalleryStyles } from './runefoble-wardrobe-gallery.styles.ts';

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
  static styles = wardrobeGalleryStyles;

  private readonly auth = new AuthConsumerController(this);
  /** One blob-backed image per variant thumbnail (TASK-0785). Keyed by variant id. */
  private readonly thumbnails = new Map<string, AssetImageController>();
  /** The active portrait. Forged portraits are protected asset paths, so they load with the bearer. */
  private readonly activeImage = new AssetImageController(this, () => this.auth.authHeaders());

  @property({ type: String }) characterId = '';
  @property({ type: String }) characterName = 'Nadia the Bard';
  @property({ type: Number }) currentHp = 34;
  @property({ type: Number }) maxHp = 34;
  @property({ type: String }) activePortraitUrl = PORTRAIT_PLACEHOLDERS.fighter;
  @property({ type: String }) basePortraitUrl = PORTRAIT_PLACEHOLDERS.fighter;
  @property({ type: String }) activeVariantId: string | null = null;
  @property({ type: Array }) conditionBadges: string[] = [];
  @property({ type: Array }) variants: WardrobeVariantItem[] = [];

  @state() private selectedAttire = 'ballroom_masquerade';
  @state() private isForging = false;

  override willUpdate(changed: PropertyValues) {
    super.willUpdate(changed);
    this.activeImage.setSource(this.activePortraitUrl);
    const liveIds = new Set(this.variants.map((v) => v.variantId));
    for (const v of this.variants) this.thumbnailFor(v.variantId).setSource(v.imageUrl);
    for (const [variantId, image] of this.thumbnails) {
      if (liveIds.has(variantId)) continue;
      image.setSource('');
      this.removeController(image);
      this.thumbnails.delete(variantId);
    }
  }

  private thumbnailFor(variantId: string): AssetImageController {
    let image = this.thumbnails.get(variantId);
    if (!image) {
      image = new AssetImageController(this, () => this.auth.authHeaders());
      this.thumbnails.set(variantId, image);
    }
    return image;
  }

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

  private renderConditionBadge(badge: string) {
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
  }

  private renderConditionBadges(badges: string[]) {
    if (badges.length === 0) {
      return html`<span class="badge-pill badge-default">Normal / Healthy</span>`;
    }
    return badges.map((badge) => this.renderConditionBadge(badge));
  }

  private renderVariantCard(v: WardrobeVariantItem) {
    const isActive = this.activeVariantId === v.variantId;
    return html`
      <div
        class="variant-card ${isActive ? 'active' : ''}"
        @click=${() => this.handleSelectVariant(v)}
      >
        <img class="variant-thumbnail" src="${this.thumbnailFor(v.variantId).url}" alt="${v.variantName}" />
        <div class="variant-name" title="${v.variantName}">${v.variantName}</div>
        <button class="btn-equip ${isActive ? 'active-btn' : ''}">
          ${isActive ? 'Active' : 'Equip'}
        </button>
      </div>
    `;
  }

  private renderHeader(isBloodied: boolean) {
    return html`
      <div class="gallery-header">
        <span class="header-title">Wardrobe & State Gallery</span>
        <span class="hp-badge ${isBloodied ? 'low' : ''}">
          HP: ${this.currentHp} / ${this.maxHp}
        </span>
      </div>
    `;
  }

  private renderActiveSection(badges: string[], isBloodied: boolean, isPoisoned: boolean) {
    return html`
      <div class="active-section">
        <div class="avatar-wrapper">
          <img
            class="avatar-img ${isBloodied ? 'bloodied' : ''} ${isPoisoned ? 'poisoned' : ''}"
            src="${this.activeImage.url}"
            alt="${this.characterName} Active Portrait"
          />
        </div>
        <div class="active-info">
          <div class="character-name">${this.characterName}</div>
          <div class="condition-badges-row">
            ${this.renderConditionBadges(badges)}
          </div>
        </div>
      </div>
    `;
  }

  private renderForgePanel() {
    return html`
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

  render() {
    const badges = this.getEffectiveBadges();
    const isBloodied = badges.includes('bloodied');
    const isPoisoned = badges.includes('poisoned');

    return html`
      ${this.renderHeader(isBloodied)}
      ${this.renderActiveSection(badges, isBloodied, isPoisoned)}

      <div class="variants-title">Unlocked Wardrobe Variants (${this.variants.length})</div>
      <div class="variants-grid">
        ${this.variants.map((v) => this.renderVariantCard(v))}
      </div>

      ${this.renderForgePanel()}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-wardrobe-gallery': RunefobleWardrobeGallery;
  }
}
