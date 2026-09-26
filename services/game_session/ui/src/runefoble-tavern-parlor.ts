import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { tavernParlorStyles } from './runefoble-tavern-parlor.styles.ts';

export interface LiarsDiceBid {
  quantity: number;
  face: number;
  bidder: string;
}

@customElement('runefoble-tavern-parlor')
export class RunefobleTavernParlor extends LitElement {
  static styles = [tavernParlorStyles];

  @property({ type: String, attribute: 'session-id' }) sessionId = 'session-tavern-1';
  @property({ type: String, attribute: 'campaign-id' }) campaignId = 'campaign-1';
  @property({ type: String, attribute: 'character-id' }) characterId = 'char-bram';
  @property({ type: String, attribute: 'character-name' }) characterName = 'Bram the Tinkerer';

  @property({ type: String }) activeTab: 'dice' | 'drinking' | 'merchant' = 'dice';
  @property({ type: Number }) wagerGold = 10;
  @property({ type: Array }) diceRolls: number[] = [2, 3, 3, 5, 6];
  @property({ type: Boolean }) isShaking = false;
  @property({ type: Boolean }) revealed = false;

  @property({ type: Object }) currentBid: LiarsDiceBid | null = null;
  @state() private bidQuantity = 2;
  @state() private bidFace = 3;

  @property({ type: String }) intoxicationLevel: 'sober' | 'tipsy' | 'drunk' | 'smashed' | 'blackout' = 'sober';
  @property({ type: Number }) drinksConsumed = 0;
  @property({ type: Boolean }) dspActive = false;

  @property({ type: String }) merchantName = 'Thorin Stoneforged';
  @property({ type: String }) merchantTemperament = 'stubborn_greedy';
  @property({ type: Number }) merchantMoodScore = 0;
  @property({ type: Number }) basePrice = 50;
  @property({ type: Number }) offeredPrice = 35;
  @property({ type: Number }) lastCounterOffer: number | null = null;
  @property({ type: String }) lastVoiceBark: string | null = null;

  private shakeCup() {
    this.isShaking = true;
    setTimeout(() => {
      this.diceRolls = Array.from({ length: 5 }, () => Math.floor(Math.random() * 6) + 1).sort();
      this.isShaking = false;
      this.revealed = false;
    }, 600);
  }

  private handleBid() {
    const bid: LiarsDiceBid = {
      quantity: this.bidQuantity,
      face: this.bidFace,
      bidder: this.characterId,
    };
    this.currentBid = bid;
    this.dispatchEvent(
      new CustomEvent('minigame-turn-taken', {
        bubbles: true,
        composed: true,
        detail: { action: 'bid', ...bid },
      })
    );
  }

  private handleChallenge() {
    this.revealed = true;
    this.dispatchEvent(
      new CustomEvent('liars-dice-challenged', {
        bubbles: true,
        composed: true,
        detail: { challengerId: this.characterId, currentBid: this.currentBid },
      })
    );
  }

  private handleDrink() {
    this.drinksConsumed += 1;
    const stages: Array<'sober' | 'tipsy' | 'drunk' | 'smashed' | 'blackout'> = [
      'sober', 'tipsy', 'drunk', 'smashed', 'blackout',
    ];
    const nextIdx = Math.min(stages.length - 1, Math.floor(this.drinksConsumed / 2));
    this.intoxicationLevel = stages[nextIdx];
    this.dspActive = nextIdx >= 2;

    this.dispatchEvent(
      new CustomEvent('drink-taken', {
        bubbles: true,
        composed: true,
        detail: {
          characterId: this.characterId,
          drinksConsumed: this.drinksConsumed,
          intoxicationLevel: this.intoxicationLevel,
          dspActive: this.dspActive,
        },
      })
    );
  }

  private handleHaggle() {
    // Bram counters 50g with 35g against stubborn_greedy dwarven blacksmith -> counters 42g
    if (this.merchantTemperament === 'stubborn_greedy' && this.basePrice === 50 && this.offeredPrice === 35) {
      this.lastCounterOffer = 42;
      this.lastVoiceBark = "Dwarven steel doesn't bend for pennies! Meet me at 42 gold, or keep walkin'!";
    } else {
      this.lastCounterOffer = Math.ceil(this.offeredPrice + (this.basePrice - this.offeredPrice) * 0.5);
      this.lastVoiceBark = `I canna accept ${this.offeredPrice}, but I will part with it for ${this.lastCounterOffer} gold.`;
    }

    this.dispatchEvent(
      new CustomEvent('haggling-submitted', {
        bubbles: true,
        composed: true,
        detail: {
          characterId: this.characterId,
          basePrice: this.basePrice,
          offeredPrice: this.offeredPrice,
          counterOffer: this.lastCounterOffer,
        },
      })
    );
  }

  render() {
    return html`
      <div class="header-banner">
        <div class="title-group">
          <h2>Tavern Parlor & Merchant Bazaar</h2>
          <p>Liar's Dice wagering, drinking contests, and social bartering.</p>
        </div>
        <div style="font-weight: 700; font-size: 0.85rem;">
          Wager Pot: <strong style="color: #d97706;">${this.wagerGold * 2} GP</strong>
        </div>
      </div>

      <div class="tab-bar">
        <button
          class="tab-btn ${this.activeTab === 'dice' ? 'active' : ''}"
          @click="${() => { this.activeTab = 'dice'; }}"
        >
          🎲 Liar's Dice
        </button>
        <button
          class="tab-btn ${this.activeTab === 'drinking' ? 'active' : ''}"
          @click="${() => { this.activeTab = 'drinking'; }}"
        >
          🍺 Drinking Contest
        </button>
        <button
          class="tab-btn ${this.activeTab === 'merchant' ? 'active' : ''}"
          @click="${() => { this.activeTab = 'merchant'; }}"
        >
          ⚖️ Merchant Haggling
        </button>
      </div>

      ${this.activeTab === 'dice' ? this.renderDiceTab() : ''}
      ${this.activeTab === 'drinking' ? this.renderDrinkingTab() : ''}
      ${this.activeTab === 'merchant' ? this.renderMerchantTab() : ''}
    `;
  }

  private renderDiceTab() {
    return html`
      <div class="panel">
        <div class="shaker-stage">
          <div
            class="dice-cup ${this.isShaking ? 'shaking' : ''}"
            title="Click to shake dice"
            @click="${this.shakeCup}"
          ></div>
          <p style="color: #cbd5e1; font-size: 0.8rem; margin: 8px 0 0 0;">
            ${this.isShaking ? 'Rattling dice cup...' : 'Click cup to rattle and roll'}
          </p>
        </div>

        <div style="text-align: center; font-weight: 700; font-size: 0.85rem;">
          Your Dice Hand (${this.revealed ? 'Revealed' : 'Under Cup'})
        </div>
        <div class="dice-tray">
          ${this.diceRolls.map(
            (val) => html`<div class="die-box ${val === 1 ? 'wild' : ''}">${val}</div>`
          )}
        </div>

        ${this.currentBid
          ? html`
              <div style="background: #f1f5f9; padding: 10px; border: 1px solid #cbd5e1; margin-top: 12px; text-align: center;">
                <strong>Current Bid:</strong> ${this.currentBid.quantity}x of Face [${this.currentBid.face}]
                by <em>${this.currentBid.bidder}</em>
              </div>
            `
          : ''}

        <div class="bidding-controls">
          <div class="stepper-group">
            <label style="font-weight: 700; font-size: 0.8rem;">Quantity:</label>
            <button class="stepper-btn" @click="${() => { if (this.bidQuantity > 1) this.bidQuantity--; }}">-</button>
            <span style="font-weight: 800; min-width: 20px; text-align: center;">${this.bidQuantity}</span>
            <button class="stepper-btn" @click="${() => this.bidQuantity++}">+</button>
          </div>
          <div class="stepper-group">
            <label style="font-weight: 700; font-size: 0.8rem;">Face Value:</label>
            <button class="stepper-btn" @click="${() => { if (this.bidFace > 1) this.bidFace--; }}">-</button>
            <span style="font-weight: 800; min-width: 20px; text-align: center;">${this.bidFace}</span>
            <button class="stepper-btn" @click="${() => { if (this.bidFace < 6) this.bidFace++; }}">+</button>
          </div>
        </div>

        <div style="display: flex; gap: 10px; margin-top: 14px;">
          <button class="btn btn-gold" style="flex: 1;" @click="${this.handleBid}">
            Raise Bid / Bluff
          </button>
          <button
            class="btn btn-challenge"
            style="flex: 1;"
            ?disabled="${!this.currentBid}"
            @click="${this.handleChallenge}"
          >
            Call Bluff / Liar!
          </button>
        </div>
      </div>
    `;
  }

  private renderDrinkingTab() {
    return html`
      <div class="panel">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-weight: 800; text-transform: uppercase;">Intoxication Level</span>
          ${this.dspActive
            ? html`<span class="dsp-badge">🎙️ Voice DSP Slurred Filter: Active</span>`
            : html`<span style="font-size: 0.75rem; color: #64748b;">Voice: Clear</span>`}
        </div>

        <div class="intox-bar">
          <div class="intox-fill ${this.intoxicationLevel}"></div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.75rem; font-weight: 700;">
          <span>Sober</span>
          <span>Tipsy</span>
          <span>Drunk</span>
          <span>Smashed</span>
          <span>Blackout</span>
        </div>

        <div style="margin-top: 16px; display: flex; align-items: center; justify-content: space-between;">
          <span>Pints Consumed: <strong>${this.drinksConsumed}</strong></span>
          <button class="btn btn-drink" @click="${this.handleDrink}">
            🍺 Take a Drink (DC ${10 + this.drinksConsumed * 2})
          </button>
        </div>
      </div>
    `;
  }

  private renderMerchantTab() {
    return html`
      <div class="panel">
        <div class="merchant-grid">
          <div>
            <div style="font-weight: 800; font-size: 1.1rem;">${this.merchantName}</div>
            <span class="temperament-tag">Temperament: ${this.merchantTemperament.replace('_', ' ')}</span>
            <div style="margin-top: 10px; font-size: 0.85rem;">
              Base Quote: <strong>${this.basePrice} GP</strong>
            </div>
            <div style="margin-top: 6px; font-size: 0.85rem;">
              Your Offer: <strong>${this.offeredPrice} GP</strong>
            </div>
          </div>
          <div>
            <button class="btn btn-gold" style="width: 100%; margin-top: 10px;" @click="${this.handleHaggle}">
              Counter & Persuade
            </button>
            ${this.lastCounterOffer
              ? html`<div class="counter-badge">Counter Offer: ${this.lastCounterOffer} GP</div>`
              : ''}
          </div>
        </div>

        ${this.lastVoiceBark
          ? html`
              <div class="voice-bark-box">
                <strong>"${this.merchantName}":</strong> ${this.lastVoiceBark}
              </div>
            `
          : ''}
      </div>
    `;
  }
}
