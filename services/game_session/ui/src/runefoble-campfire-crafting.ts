import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { campfireCraftingStyles } from './runefoble-campfire-crafting.styles.ts';

export interface CraftingOutcome {
  outcome: 'success' | 'mishap';
  message: string;
  item_name?: string;
  tags?: string[];
}

@customElement('runefoble-campfire-crafting')
export class RunefobleCampfireCrafting extends LitElement {
  static styles = [campfireCraftingStyles];

  @property({ type: String, attribute: 'session-id' }) sessionId = 'session-1';
  @property({ type: String, attribute: 'campaign-id' }) campaignId = 'campaign-1';
  @property({ type: String, attribute: 'character-id' }) characterId = 'char-bram';
  @property({ type: String, attribute: 'character-name' }) characterName = 'Bram the Tinkerer';
  @property({ type: String, attribute: 'rest-type' }) restType: 'short' | 'long' = 'long';
  @property({ type: String, attribute: 'storytelling-prompt' }) storytellingPrompt =
    'The crackling embers cast flickering warmth across tired faces. Tell a tale of the first monster that truly frightened your character.';

  @property({ type: Array }) availableReagents: string[] = [
    'Glowmoss Extract',
    'Volcano Ash',
    'Star Lily',
    'Nightshade Berry',
    'Purified Quicksilver',
  ];

  @property({ type: Array }) selectedReagents: string[] = [];
  @property({ type: String }) selectedCatalyst = 'none';
  @property({ type: Object }) strongholdFacilities: Record<string, number> = {
    watchtower: 1,
    herbal_rack: 1,
    arcane_forge: 0,
  };
  @property({ type: Array }) activeBoons: string[] = [
    'Campfire Camaraderie (+1 Morale to Initiative)',
    'Vigilant Sentry (+2 Passive Perception)',
    'Restorative Brews (+1d4 Rest Healing)',
  ];
  @property({ type: Object }) lastOutcome: CraftingOutcome | null = null;

  @state() private calculatedRisk = 0.25;

  private toggleReagent(reagent: string) {
    if (this.selectedReagents.includes(reagent)) {
      this.selectedReagents = this.selectedReagents.filter((r) => r !== reagent);
    } else {
      if (this.selectedReagents.length >= 3) return;
      this.selectedReagents = [...this.selectedReagents, reagent];
    }
    this.updateRisk();
  }

  private handleCatalystChange(e: Event) {
    const target = e.target as HTMLSelectElement;
    this.selectedCatalyst = target.value;
    this.updateRisk();
  }

  private updateRisk() {
    let risk = 0.15;
    if (this.selectedReagents.includes('Volcano Ash')) risk += 0.25;
    if (this.selectedReagents.includes('Nightshade Berry')) risk += 0.2;
    if (this.selectedReagents.includes('Glowmoss Extract') && this.selectedReagents.includes('Volcano Ash')) {
      risk -= 0.1; // Recipe affinity synergy
    }
    if (this.selectedCatalyst === 'purified_water') risk -= 0.15;
    if (this.selectedCatalyst === 'dragon_bile') risk += 0.15;
    this.calculatedRisk = Math.max(0.05, Math.min(0.95, Math.round(risk * 100) / 100));
  }

  private handleCombine() {
    if (this.selectedReagents.length === 0) return;

    let outcome: CraftingOutcome;
    if (
      this.selectedReagents.includes('Glowmoss Extract') &&
      this.selectedReagents.includes('Volcano Ash')
    ) {
      outcome = {
        outcome: 'success',
        item_name: 'Radiant Smoke Pellet',
        message: 'Synthesized 1x Radiant Smoke Pellet! Illumination and smoke burst ready.',
        tags: ['consumable', 'radiant', 'obscurement', 'aoe'],
      };
    } else if (this.calculatedRisk > 0.5 && this.selectedCatalyst === 'none') {
      outcome = {
        outcome: 'mishap',
        message: 'Volatile Reaction! Crucible exploded with caustic purple fumes. Crafter takes 4 damage.',
      };
    } else {
      outcome = {
        outcome: 'success',
        item_name: `Experimental Brew (${this.selectedReagents.join(' & ')})`,
        message: `Successfully synthesized novel concoction from ${this.selectedReagents.length} reagents.`,
        tags: ['experimental', 'consumable'],
      };
    }

    this.lastOutcome = outcome;
    this.dispatchEvent(
      new CustomEvent('reagents-combined', {
        bubbles: true,
        composed: true,
        detail: {
          characterId: this.characterId,
          reagents: [...this.selectedReagents],
          catalyst: this.selectedCatalyst,
          outcome,
        },
      })
    );
  }

  private handleRest() {
    this.dispatchEvent(
      new CustomEvent('campfire-rest-requested', {
        bubbles: true,
        composed: true,
        detail: {
          sessionId: this.sessionId,
          restType: this.restType,
          prompt: this.storytellingPrompt,
        },
      })
    );
  }

  private handleUpgrade(facility: string) {
    this.dispatchEvent(
      new CustomEvent('stronghold-upgrade-requested', {
        bubbles: true,
        composed: true,
        detail: {
          campaignId: this.campaignId,
          facility,
        },
      })
    );
  }

  render() {
    const riskPercentage = Math.round(this.calculatedRisk * 100);
    const riskClass = this.calculatedRisk < 0.35 ? 'low' : this.calculatedRisk < 0.6 ? 'med' : 'high';

    return html`
      <div class="header-banner">
        <div class="title-group">
          <h2>Campfire Downtime & Laboratory</h2>
          <p>Resting, reagent experimentation, and party campsite fortification.</p>
        </div>
        <div class="character-badge">
          <strong>Artisan:</strong> ${this.characterName}
        </div>
      </div>

      <div class="grid-layout">
        <!-- Campfire & Storytelling Panel -->
        <div class="panel campfire-box">
          <div class="panel-header">
            <span>🔥</span> Campfire Rest Interlude
          </div>
          <div class="prompt-quote">
            "${this.storytellingPrompt}"
          </div>

          <div class="rest-controls">
            <div class="rest-toggle">
              <button
                class="${this.restType === 'short' ? 'active' : ''}"
                @click="${() => { this.restType = 'short'; }}"
              >
                Short Rest
              </button>
              <button
                class="${this.restType === 'long' ? 'active' : ''}"
                @click="${() => { this.restType = 'long'; }}"
              >
                Long Rest
              </button>
            </div>
            <button class="btn btn-flame" @click="${this.handleRest}">
              Rest by Campfire
            </button>
          </div>

          <div style="margin-top: 16px;">
            <div style="font-weight: 700; font-size: 0.85rem; text-transform: uppercase;">
              Active Party Rest Boons
            </div>
            <div class="boons-tag-list">
              ${this.activeBoons.map(
                (boon) => html`<span class="boon-tag">✦ ${boon}</span>`
              )}
            </div>
          </div>
        </div>

        <!-- Stronghold Campsite Facilities -->
        <div class="panel">
          <div class="panel-header">
            <span>🏰</span> Campsite Fortifications
          </div>
          <div class="facility-list">
            <div class="facility-row">
              <div>
                <span class="facility-name">Watchtower</span>
                <span class="facility-tier">Tier ${this.strongholdFacilities.watchtower || 0}</span>
              </div>
              <button class="btn" @click="${() => this.handleUpgrade('watchtower')}">
                Upgrade
              </button>
            </div>

            <div class="facility-row">
              <div>
                <span class="facility-name">Herbal Drying Rack</span>
                <span class="facility-tier">Tier ${this.strongholdFacilities.herbal_rack || 0}</span>
              </div>
              <button class="btn" @click="${() => this.handleUpgrade('herbal_rack')}">
                Upgrade
              </button>
            </div>

            <div class="facility-row">
              <div>
                <span class="facility-name">Arcane Forge</span>
                <span class="facility-tier">Tier ${this.strongholdFacilities.arcane_forge || 0}</span>
              </div>
              <button class="btn" @click="${() => this.handleUpgrade('arcane_forge')}">
                Upgrade
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Alchemical Crucible Workbench -->
      <div class="panel" style="margin-top: 20px;">
        <div class="panel-header">
          <span>⚗️</span> Alchemical Crucible Workbench
        </div>

        <div style="font-weight: 700; font-size: 0.85rem; margin-bottom: 6px;">Available Reagents</div>
        <div class="reagents-tray">
          ${this.availableReagents.map(
            (r) => html`
              <span
                class="chip ${this.selectedReagents.includes(r) ? 'selected' : ''}"
                @click="${() => this.toggleReagent(r)}"
              >
                ${this.selectedReagents.includes(r) ? '✓ ' : '+ '} ${r}
              </span>
            `
          )}
        </div>

        <div class="crucible-chamber">
          <div class="crucible-title">Crucible Mixing Chamber (Max 3 Reagents)</div>
          <div class="crucible-slots">
            ${this.selectedReagents.length === 0
              ? html`<span style="color: #64748b; font-style: italic;">Select reagents from tray above...</span>`
              : this.selectedReagents.map(
                  (r) => html`<span class="chip selected">${r}</span>`
                )}
          </div>
        </div>

        <div class="catalyst-selector">
          <label><strong>Catalyst:</strong></label>
          <select @change="${this.handleCatalystChange}">
            <option value="none">None (Raw Mix)</option>
            <option value="purified_water">Purified Spring Water (-20% Risk)</option>
            <option value="dragon_bile">Dragon Bile (+2 Potency, +15% Risk)</option>
            <option value="quicksilver">Purified Quicksilver (Stabilizer)</option>
            <option value="spirit_ash">Spirit Ash (Blessed Radiant)</option>
          </select>
        </div>

        <div class="risk-meter">
          <div class="risk-header">
            <span>Volatile Mishap Probability:</span>
            <span>${riskPercentage}%</span>
          </div>
          <div class="risk-bar">
            <div class="risk-fill ${riskClass}" style="width: ${riskPercentage}%"></div>
          </div>
        </div>

        <button
          class="btn btn-primary"
          ?disabled="${this.selectedReagents.length === 0}"
          @click="${this.handleCombine}"
        >
          Transmute & Combine Reagents
        </button>

        ${this.lastOutcome
          ? html`
              <div class="outcome-box ${this.lastOutcome.outcome}">
                <strong>${this.lastOutcome.outcome === 'success' ? 'Alchemy Success:' : 'Mishap Alert:'}</strong>
                <p style="margin: 4px 0 0 0;">${this.lastOutcome.message}</p>
                ${this.lastOutcome.tags
                  ? html`
                      <div style="margin-top: 6px; display: flex; gap: 4px;">
                        ${this.lastOutcome.tags.map(
                          (t) => html`<span class="boon-tag">${t}</span>`
                        )}
                      </div>
                    `
                  : ''}
              </div>
            `
          : ''}
      </div>
    `;
  }
}
