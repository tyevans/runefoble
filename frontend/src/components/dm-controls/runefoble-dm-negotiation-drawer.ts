import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { dmNegotiationDrawerStyles } from './runefoble-dm-negotiation-drawer.styles.ts';

@customElement('runefoble-dm-negotiation-drawer')
export class RunefobleDMNegotiationDrawer extends LitElement {
  static styles = [dmNegotiationDrawerStyles];

  @property({ type: String, attribute: 'negotiation-id' }) negotiationId = 'neg-default-1';
  @property({ type: String, attribute: 'merchant-name' }) merchantName = 'Torvin Ironbreaker';
  @property({ type: String, attribute: 'character-name' }) characterName = 'Lady Nicole';
  @property({ type: String, attribute: 'item-name' }) itemName = 'Folded Adamantine Blade';
  @property({ type: Number, attribute: 'original-price' }) originalPrice = 350;
  @property({ type: Number, attribute: 'current-offer' }) currentOffer = 260;
  @property({ type: Number, attribute: 'counter-price' }) counterPrice = 300;
  @property({ type: Number }) patience = 4;
  @property({ type: String }) status = 'active';

  @state() private customBark = 'Torvin scowls, then nods in begrudging respect. Done.';
  @state() private overridePriceInput = 280;

  private triggerOverride(action: string, overridePrice?: number, bark?: string) {
    this.dispatchEvent(
      new CustomEvent('dm-override', {
        bubbles: true,
        composed: true,
        detail: {
          negotiationId: this.negotiationId,
          action,
          overridePrice: overridePrice ?? this.overridePriceInput,
          narrativeBark: bark ?? this.customBark,
        },
      })
    );
  }

  private handleBroadcastBark() {
    this.triggerOverride('force_accept', this.overridePriceInput, this.customBark);
  }

  render() {
    return html`
      <div class="dm-drawer">
        <div class="drawer-header">
          <div class="drawer-title">
            <span class="dm-badge">DM Control</span>
            <h4>Arbitration Panel: ${this.merchantName}</h4>
          </div>
          <span class="status-tag ${this.status}">${this.status}</span>
        </div>

        <div class="drawer-body">
          <!-- Live Telemetry -->
          <div class="telemetry-bar">
            <div class="telemetry-item">
              <div class="telemetry-label">Customer</div>
              <div class="telemetry-value">${this.characterName}</div>
            </div>
            <div class="telemetry-item">
              <div class="telemetry-label">Item</div>
              <div class="telemetry-value">${this.itemName}</div>
            </div>
            <div class="telemetry-item">
              <div class="telemetry-label">Current Offer</div>
              <div class="telemetry-value">${this.currentOffer} GP</div>
            </div>
            <div class="telemetry-item">
              <div class="telemetry-label">Counter</div>
              <div class="telemetry-value">${this.counterPrice} GP</div>
            </div>
            <div class="telemetry-item">
              <div class="telemetry-label">Patience</div>
              <div class="telemetry-value">${this.patience} / 5</div>
            </div>
          </div>

          <!-- One-Click Mood Modifiers -->
          <div class="section-label">One-Click DM Mood Modifiers</div>
          <div class="modifier-grid">
            <button
              class="dm-btn btn-soothe"
              @click=${() => this.triggerOverride('soothe_merchant', undefined, 'The DM soothes the merchant with a calm gesture.')}
            >
              🌿 Soothe Merchant (+2 Pts)
            </button>
            <button
              class="dm-btn btn-enrage"
              @click=${() => this.triggerOverride('enrage_merchant', undefined, 'The merchant snaps with sudden rage!')}
            >
              🔥 Enrage Merchant (-2 Pts)
            </button>
            <button
              class="dm-btn btn-accept"
              @click=${() => this.triggerOverride('accept_deal', this.currentOffer, 'DM accepts trade at customer offer.')}
            >
              ✅ Accept Deal (${this.currentOffer} GP)
            </button>
            <button
              class="dm-btn btn-refuse"
              @click=${() => this.triggerOverride('refuse_kick_out', undefined, 'The DM orders the merchant to refuse and kick out the party.')}
            >
              🚫 Refuse & Kick Out
            </button>
          </div>

          <!-- Custom Bark & Price Override Form -->
          <div class="bark-injection-box">
            <div class="section-label">Custom Bark & Override Injection</div>
            <div class="input-row">
              <input
                type="text"
                class="bark-input"
                .value=${this.customBark}
                @input=${(e: Event) => (this.customBark = (e.target as HTMLInputElement).value)}
                placeholder="In-character merchant dialogue bark..."
              />
              <input
                type="number"
                class="price-override-input"
                .value=${String(this.overridePriceInput)}
                @input=${(e: Event) => (this.overridePriceInput = parseInt((e.target as HTMLInputElement).value, 10) || 0)}
                placeholder="Price"
              />
              <button class="btn-broadcast" @click=${this.handleBroadcastBark}>
                Broadcast
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
  }
}
