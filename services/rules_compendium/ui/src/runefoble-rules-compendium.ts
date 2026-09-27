/**
 * Lit Web Component: <runefoble-rules-compendium>
 * Root Microfrontend for TTRPG Rules Compendium and CR Encounter Builder.
 * Governed by ADR-0001, ADR-0003, ADR-0004, ADR-0007, and ADR-0013.
 */

import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { compendiumStyles } from './runefoble-rules-compendium.styles.ts';
import './runefoble-rules-lookup.ts';
import './runefoble-encounter-builder.ts';
import './runefoble-homebrew-creator.ts';
import type { DifficultyTier, DraftMonsterEntry } from './types.ts';

@customElement('runefoble-rules-compendium')
export class RunefobleRulesCompendium extends LitElement {
  static styles = [compendiumStyles];

  @property({ type: String }) apiBaseUrl = '';
  @property({ type: String }) campaignId: string | null = null;
  @property({ type: String }) userId: string | null = null;
  @property({ type: Boolean }) isDM = false;
  @property({ type: String }) activeTab: 'search' | 'encounter' | 'homebrew' = 'search';

  @property({ type: Array }) partyLevels: number[] = [3, 3, 3, 3];
  @property({ type: String }) targetDifficulty: DifficultyTier = 'Medium';
  @property({ type: Array }) draftMonsters: DraftMonsterEntry[] = [];

  private handleTabSelect(tab: 'search' | 'encounter' | 'homebrew') {
    this.activeTab = tab;
    this.dispatchEvent(
      new CustomEvent('tab-changed', {
        detail: { tab },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleMonsterAddedFromLookup(e: CustomEvent<{ monster: DraftMonsterEntry }>) {
    const m = e.detail.monster;
    const existing = this.draftMonsters.find((item) => item.name === m.name);
    if (existing) {
      existing.count += 1;
      this.draftMonsters = [...this.draftMonsters];
    } else {
      this.draftMonsters = [...this.draftMonsters, { ...m, count: 1 }];
    }
    this.requestUpdate();
  }

  render() {
    return html`
      <div class="compendium-header">
        <div class="title-group">
          <div class="main-title">
            <span>⚔️ Rules Compendium</span>
          </div>
          <div class="subtitle">
            SRD 5.1 Redstring Hybrid Search & Automated CR Encounter Builder
            ${this.campaignId ? html` • Campaign: <code>${this.campaignId}</code>` : ''}
          </div>
        </div>

        <div class="tabs-nav">
          <button
            class="tab-btn ${this.activeTab === 'search' ? 'active' : ''}"
            @click=${() => this.handleTabSelect('search')}
          >
            📖 Search Rules
          </button>
          <button
            class="tab-btn ${this.activeTab === 'encounter' ? 'active' : ''}"
            @click=${() => this.handleTabSelect('encounter')}
          >
            🛡️ CR Builder (${this.draftMonsters.reduce((acc, m) => acc + m.count, 0)})
          </button>
          <button
            class="tab-btn ${this.activeTab === 'homebrew' ? 'active' : ''}"
            @click=${() => this.handleTabSelect('homebrew')}
          >
            ✨ Homebrew Forge
          </button>
        </div>
      </div>

      ${this.activeTab === 'search' ? this.renderSearchTab() : ''}
      ${this.activeTab === 'encounter' ? this.renderEncounterTab() : ''}
      ${this.activeTab === 'homebrew' ? this.renderHomebrewTab() : ''}
    `;
  }

  private renderSearchTab() {
    return html`
      <runefoble-rules-lookup
        .apiBaseUrl=${this.apiBaseUrl}
        .campaignId=${this.campaignId}
        .userId=${this.userId}
        @monster-added=${this.handleMonsterAddedFromLookup}
      ></runefoble-rules-lookup>
    `;
  }

  private renderEncounterTab() {
    return html`
      <runefoble-encounter-builder
        .apiBaseUrl=${this.apiBaseUrl}
        .campaignId=${this.campaignId}
        .partyLevels=${this.partyLevels}
        .targetDifficulty=${this.targetDifficulty}
        .draftMonsters=${this.draftMonsters}
      ></runefoble-encounter-builder>
    `;
  }

  private renderHomebrewTab() {
    return html`
      <runefoble-homebrew-creator
        .apiBaseUrl=${this.apiBaseUrl}
        .campaignId=${this.campaignId}
        .userId=${this.userId}
        .isDM=${this.isDM}
      ></runefoble-homebrew-creator>
    `;
  }
}
