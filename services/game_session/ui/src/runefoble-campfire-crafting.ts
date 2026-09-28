import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { campfireCraftingStyles } from './runefoble-campfire-crafting.styles.ts';
import {
  DEFAULT_BOONS, DEFAULT_FACILITIES, DEFAULT_PROMPT, DEFAULT_REAGENTS,
  renderBoonsDisplay, renderCraftingBench, renderStrongholdStatus,
} from './campfire/index.ts';
import type { CraftingOutcome } from './campfire/index.ts';
export type { CraftingOutcome };

@customElement('runefoble-campfire-crafting')
export class RunefobleCampfireCrafting extends LitElement {
  static styles = [campfireCraftingStyles];

  @property({ type: String, attribute: 'session-id' }) sessionId = 'session-1';
  @property({ type: String, attribute: 'campaign-id' }) campaignId = 'campaign-1';
  @property({ type: String, attribute: 'character-id' }) characterId = 'char-bram';
  @property({ type: String, attribute: 'character-name' }) characterName = 'Bram the Tinkerer';
  @property({ type: String, attribute: 'rest-type' }) restType: 'short' | 'long' = 'long';
  @property({ type: String, attribute: 'storytelling-prompt' }) storytellingPrompt = DEFAULT_PROMPT;
  @property({ type: Array }) availableReagents = [...DEFAULT_REAGENTS];
  @property({ type: Array }) selectedReagents: string[] = [];
  @property({ type: String }) selectedCatalyst = 'none';
  @property({ type: Object }) strongholdFacilities = { ...DEFAULT_FACILITIES };
  @property({ type: Array }) activeBoons = [...DEFAULT_BOONS];
  @property({ type: Object }) lastOutcome: CraftingOutcome | null = null;
  @state() private calculatedRisk = 0.25;

  private toggleReagent(reagent: string) {
    if (this.selectedReagents.includes(reagent)) {
      this.selectedReagents = this.selectedReagents.filter((r) => r !== reagent);
    } else if (this.selectedReagents.length < 3) {
      this.selectedReagents = [...this.selectedReagents, reagent];
    }
    this.updateRisk();
  }
  private handleCatalystChange(e: Event) {
    this.selectedCatalyst = (e.target as HTMLSelectElement).value;
    this.updateRisk();
  }
  private updateRisk() {
    let risk = 0.15;
    if (this.selectedReagents.includes('Volcano Ash')) risk += 0.25;
    if (this.selectedReagents.includes('Nightshade Berry')) risk += 0.2;
    if (this.selectedReagents.includes('Glowmoss Extract') && this.selectedReagents.includes('Volcano Ash')) risk -= 0.1;
    if (this.selectedCatalyst === 'purified_water') risk -= 0.15;
    if (this.selectedCatalyst === 'dragon_bile') risk += 0.15;
    this.calculatedRisk = Math.max(0.05, Math.min(0.95, Math.round(risk * 100) / 100));
  }
  private handleCombine() {
    if (this.selectedReagents.length === 0) return;
    const hasSynergy = this.selectedReagents.includes('Glowmoss Extract') && this.selectedReagents.includes('Volcano Ash');
    const outcome: CraftingOutcome = hasSynergy
      ? { outcome: 'success', item_name: 'Radiant Smoke Pellet', message: 'Synthesized 1x Radiant Smoke Pellet! Illumination and smoke burst ready.', tags: ['consumable', 'radiant', 'obscurement', 'aoe'] }
      : (this.calculatedRisk > 0.5 && this.selectedCatalyst === 'none')
      ? { outcome: 'mishap', message: 'Volatile Reaction! Crucible exploded with caustic purple fumes. Crafter takes 4 damage.' }
      : { outcome: 'success', item_name: `Experimental Brew (${this.selectedReagents.join(' & ')})`, message: `Successfully synthesized novel concoction from ${this.selectedReagents.length} reagents.`, tags: ['experimental', 'consumable'] };
    this.lastOutcome = outcome;
    this.dispatchEvent(new CustomEvent('reagents-combined', {
      bubbles: true, composed: true,
      detail: { characterId: this.characterId, reagents: [...this.selectedReagents], catalyst: this.selectedCatalyst, outcome },
    }));
  }
  private handleRest() {
    this.dispatchEvent(new CustomEvent('campfire-rest-requested', {
      bubbles: true, composed: true, detail: { sessionId: this.sessionId, restType: this.restType, prompt: this.storytellingPrompt },
    }));
  }
  private handleUpgrade(facility: string) {
    this.dispatchEvent(new CustomEvent('stronghold-upgrade-requested', {
      bubbles: true, composed: true, detail: { campaignId: this.campaignId, facility },
    }));
  }

  render() {
    return html`
      <div class="header-banner">
        <div class="title-group"><h2>Campfire Downtime & Laboratory</h2><p>Resting, reagent experimentation, and party campsite fortification.</p></div>
        <div class="character-badge"><strong>Artisan:</strong> ${this.characterName}</div>
      </div>
      <div class="grid-layout">
        ${renderBoonsDisplay({
          storytellingPrompt: this.storytellingPrompt, restType: this.restType, activeBoons: this.activeBoons,
          onSelectRestType: (t) => { this.restType = t; }, onRest: () => this.handleRest(),
        })}
        ${renderStrongholdStatus({
          strongholdFacilities: this.strongholdFacilities, onUpgrade: (f) => this.handleUpgrade(f),
        })}
      </div>
      ${renderCraftingBench({
        availableReagents: this.availableReagents, selectedReagents: this.selectedReagents,
        selectedCatalyst: this.selectedCatalyst, calculatedRisk: this.calculatedRisk, lastOutcome: this.lastOutcome,
        onToggleReagent: (r) => this.toggleReagent(r), onCatalystChange: (e) => this.handleCatalystChange(e),
        onCombine: () => this.handleCombine(),
      })}
    `;
  }
}
