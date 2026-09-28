import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { merchantHagglerStyles } from './runefoble-merchant-haggler.styles.ts';

export interface GambitChoice {
  id: string;
  label: string;
  desc: string;
}

export const GAMBITS: GambitChoice[] = [
  { id: 'flattery', label: 'Flattery / Praise', desc: 'Appeals to artisan pride' },
  { id: 'bulk_order_promise', label: 'Bulk Order Promise', desc: 'Promises future business' },
  { id: 'point_out_flaw', label: 'Point Out Flaw', desc: 'Critiques visible flaws' },
  { id: 'hard_intimidation', label: 'Hard Intimidation', desc: 'Risky threat of force' },
  { id: 'walk_away_bluff', label: 'Walk Away Bluff', desc: 'Feigns leaving empty-handed' },
];

@customElement('runefoble-merchant-haggler')
export class RunefobleMerchantHaggler extends LitElement {
  static styles = [merchantHagglerStyles];

  @property({ type: String, attribute: 'negotiation-id' }) negotiationId = '';
  @property({ type: String, attribute: 'merchant-id' }) merchantId = 'merchant-torvin';
  @property({ type: String, attribute: 'merchant-name' }) merchantName = 'Torvin Ironbreaker';
  @property({ type: String }) temperament = 'Stubborn';
  @property({ type: Number }) patience = 5;
  @property({ type: Number, attribute: 'original-price' }) originalPrice = 100;
  @property({ type: Number, attribute: 'current-offer' }) currentOffer = 75;
  @property({ type: Number, attribute: 'counter-price' }) counterPrice = 90;
  @property({ type: String, attribute: 'item-id' }) itemId = 'blade-folded-adamantine';
  @property({ type: String, attribute: 'item-name' }) itemName = 'Folded Adamantine Blade';
  @property({ type: String, attribute: 'last-voice-bark' }) lastVoiceBark = "Dwarven steel doesn't bend for pennies! Meet me at 90 gold.";
  @property({ type: Number, attribute: 'merchant-mood-score' }) merchantMoodScore = 0;
  @property({ type: String }) status: 'active' | 'completed' | 'refused' | 'terminated' = 'active';
  @property({ type: String, attribute: 'character-id' }) characterId = 'char-bram';
  @property({ type: String, attribute: 'selected-gambit' }) selectedGambit = 'flattery';

  @state() private inputOffer = 75;

  willUpdate(changed: Map<string, unknown>) {
    if (changed.has('currentOffer')) {
      this.inputOffer = this.currentOffer;
    }
  }

  private getEmotionBadge(): { label: string; class: string } {
    if (this.status === 'refused' || this.patience <= 1) {
      return { label: 'Enraged', class: 'enraged' };
    }
    if (this.merchantMoodScore > 10) {
      return { label: 'Pleased', class: 'pleased' };
    }
    if (this.patience <= 2) {
      return { label: 'Impatient', class: 'enraged' };
    }
    return { label: 'Shrewd', class: '' };
  }

  private handleSelectGambit(id: string) {
    this.selectedGambit = id;
  }

  private handleOfferChange(e: Event) {
    const val = parseInt((e.target as HTMLInputElement).value, 10);
    if (!isNaN(val)) {
      this.inputOffer = val;
    }
  }

  private handleExecuteGambit() {
    if (this.status !== 'active') return;
    this.dispatchEvent(
      new CustomEvent('gambit-executed', {
        bubbles: true,
        composed: true,
        detail: {
          negotiationId: this.negotiationId,
          characterId: this.characterId,
          gambit: this.selectedGambit,
          offeredPrice: this.inputOffer,
        },
      })
    );
  }

  private handleAcceptDeal() {
    if (this.status !== 'active') return;
    this.dispatchEvent(
      new CustomEvent('offer-accepted', {
        bubbles: true,
        composed: true,
        detail: {
          negotiationId: this.negotiationId,
          finalPrice: this.counterPrice,
        },
      })
    );
  }

  private renderPatienceMeter() {
    const pips = [];
    for (let i = 1; i <= 5; i++) {
      const isFilled = i <= this.patience;
      let pipClass = 'patience-pip';
      if (isFilled) {
        pipClass += ' filled';
        if (this.patience <= 1) pipClass += ' danger';
        else if (this.patience <= 3) pipClass += ' warning';
      }
      pips.push(html`<div class=${pipClass}></div>`);
    }
    return pips;
  }

  render() {
    const emotion = this.getEmotionBadge();
    const progressPct = Math.min(
      100,
      Math.max(0, Math.round(((this.originalPrice - this.counterPrice) / Math.max(1, this.originalPrice - this.inputOffer)) * 100))
    );

    return html`
      <div class="merchant-haggler">
        <!-- Header: Merchant Profile & Patience -->
        <div class="haggler-header">
          <div class="merchant-profile">
            <div class="merchant-avatar">⚔️</div>
            <div class="merchant-meta">
              <h3>${this.merchantName}</h3>
              <div class="merchant-badges">
                <span class="badge badge-temperament">${this.temperament}</span>
                <span class="badge badge-emotion ${emotion.class}">${emotion.label}</span>
              </div>
            </div>
          </div>
          <div class="patience-container">
            <div class="patience-label">Merchant Patience</div>
            <div class="patience-meter">${this.renderPatienceMeter()}</div>
          </div>
        </div>

        <!-- Status Banner if inactive -->
        ${this.status !== 'active'
          ? html`<div class="status-banner ${this.status}">
              ${this.status === 'completed'
                ? `Transaction Completed at ${this.counterPrice} Gold!`
                : 'Negotiation Collapsed — Customer Dismissed!'}
            </div>`
          : ''}

        <!-- Price Tug-of-War -->
        <div class="price-section">
          <div class="price-meter-header">
            <span>Item: <strong>${this.itemName}</strong></span>
            <span>Tag: <strong>${this.originalPrice} GP</strong></span>
          </div>
          <div class="price-tug-track">
            <div class="price-tug-fill" style="width: ${progressPct}%;"></div>
          </div>
          <div class="price-tags">
            <div>Your Offer: <span class="price-tag-value">${this.inputOffer} GP</span></div>
            <div>Counter: <span class="price-tag-value">${this.counterPrice} GP</span></div>
          </div>
        </div>

        <!-- Dialogue Bark -->
        <div class="bark-box">
          "${this.lastVoiceBark}"
        </div>

        <!-- Gambits Selection -->
        <div class="gambits-label">Bargaining Gambits</div>
        <div class="gambits-grid">
          ${GAMBITS.map(
            (g) => html`
              <div
                class="gambit-card ${this.selectedGambit === g.id ? 'selected' : ''}"
                @click=${() => this.handleSelectGambit(g.id)}
                title=${g.desc}
              >
                ${g.label}
              </div>
            `
          )}
        </div>

        <!-- Offer Input & Action Buttons -->
        <div class="controls-row">
          <div class="offer-input-group">
            <input
              type="number"
              class="offer-input"
              .value=${String(this.inputOffer)}
              @input=${this.handleOfferChange}
              ?disabled=${this.status !== 'active'}
              min="1"
              max=${this.originalPrice}
            />
            <span>GP</span>
          </div>
          <button
            class="btn btn-submit"
            @click=${this.handleExecuteGambit}
            ?disabled=${this.status !== 'active'}
          >
            Execute Gambit & Offer
          </button>
          <button
            class="btn btn-accept"
            @click=${this.handleAcceptDeal}
            ?disabled=${this.status !== 'active'}
          >
            Accept (${this.counterPrice} GP)
          </button>
        </div>
      </div>
    `;
  }
}
