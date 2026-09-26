/**
 * Lit Web Component: <runefoble-encounter-builder>
 * Governed by ADR-0004, ADR-0007, and ADR-0013.
 */

import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { compendiumStyles } from './runefoble-rules-compendium.styles.ts';
import type {
  DifficultyTier,
  DraftMonsterEntry,
  EncounterBalanceResponse,
  PartyXpThresholds,
} from './types.ts';

// Standard 5e XP Thresholds by character level [Easy, Medium, Hard, Deadly]
const XP_THRESHOLDS_PER_LEVEL: Record<number, [number, number, number, number]> = {
  1: [25, 50, 75, 100],
  2: [50, 100, 150, 200],
  3: [75, 150, 225, 400],
  4: [125, 250, 375, 500],
  5: [250, 500, 750, 1100],
  6: [300, 600, 900, 1400],
  7: [350, 750, 1100, 1700],
  8: [450, 900, 1400, 2100],
  9: [550, 1100, 1600, 2400],
  10: [600, 1200, 1900, 2800],
  11: [800, 1600, 2400, 3600],
  12: [1000, 2000, 3000, 4500],
  13: [1100, 2200, 3400, 5100],
  14: [1250, 2500, 3800, 5700],
  15: [1400, 2800, 4300, 6400],
  16: [1600, 3200, 4800, 7200],
  17: [2000, 3900, 5900, 8800],
  18: [2100, 4200, 6300, 9500],
  19: [2400, 4900, 7300, 10900],
  20: [2800, 5700, 8500, 12700],
};

@customElement('runefoble-encounter-builder')
export class RunefobleEncounterBuilder extends LitElement {
  static styles = [compendiumStyles];

  @property({ type: String }) apiBaseUrl = '';
  @property({ type: String }) campaignId: string | null = null;
  @property({ type: Array }) partyLevels: number[] = [3, 3, 3, 3];
  @property({ type: String }) targetDifficulty: DifficultyTier = 'Medium';
  @property({ type: Array }) draftMonsters: DraftMonsterEntry[] = [];

  @state() loading = false;
  @state() tacticalSummary = '';
  @state() lastBalancedResponse: EncounterBalanceResponse | null = null;

  public computePartyThresholds(): PartyXpThresholds {
    const t = { easy: 0, medium: 0, hard: 0, deadly: 0 };
    for (const lvl of this.partyLevels) {
      const clampLvl = Math.max(1, Math.min(20, lvl));
      const row = XP_THRESHOLDS_PER_LEVEL[clampLvl] || [25, 50, 75, 100];
      t.easy += row[0];
      t.medium += row[1];
      t.hard += row[2];
      t.deadly += row[3];
    }
    return t;
  }

  public computeMultiplier(count: number, partySize: number): number {
    if (count <= 0) return 1.0;
    const tiers = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0];
    let idx = 0;
    if (count === 1) idx = 0;
    else if (count === 2) idx = 1;
    else if (count <= 6) idx = 2;
    else if (count <= 10) idx = 3;
    else if (count <= 14) idx = 4;
    else idx = 5;

    if (partySize < 3 && idx < tiers.length - 1) idx += 1;
    else if (partySize >= 6 && idx > 0) idx -= 1;

    return tiers[idx];
  }

  public getLethalityTier(adjustedXp: number, thresholds: PartyXpThresholds): string {
    if (adjustedXp >= thresholds.deadly) return 'deadly';
    if (adjustedXp >= thresholds.hard) return 'hard';
    if (adjustedXp >= thresholds.medium) return 'medium';
    if (adjustedXp >= thresholds.easy) return 'easy';
    return 'trivial';
  }

  public addMonster(monster: DraftMonsterEntry) {
    const existing = this.draftMonsters.find((m) => m.name === monster.name);
    if (existing) {
      existing.count += 1;
      this.draftMonsters = [...this.draftMonsters];
    } else {
      this.draftMonsters = [...this.draftMonsters, { ...monster, count: monster.count || 1 }];
    }
    this.requestUpdate();
  }

  public removeMonster(name: string) {
    const existing = this.draftMonsters.find((m) => m.name === name);
    if (existing) {
      if (existing.count > 1) {
        existing.count -= 1;
        this.draftMonsters = [...this.draftMonsters];
      } else {
        this.draftMonsters = this.draftMonsters.filter((m) => m.name !== name);
      }
      this.requestUpdate();
    }
  }

  private setPartySize(size: number) {
    const count = Math.max(1, Math.min(8, size));
    const avgLevel = this.partyLevels.length > 0 ? this.partyLevels[0] : 3;
    this.partyLevels = Array(count).fill(avgLevel);
    this.requestUpdate();
  }

  private setPartyLevel(level: number) {
    const lvl = Math.max(1, Math.min(20, level));
    this.partyLevels = this.partyLevels.map(() => lvl);
    this.requestUpdate();
  }

  public async autoBalanceEncounter() {
    this.loading = true;
    try {
      if (this.apiBaseUrl) {
        const res = await fetch(`${this.apiBaseUrl}/api/v1/compendium/encounters/balance`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            party_levels: this.partyLevels,
            target_difficulty: this.targetDifficulty,
            campaign_id: this.campaignId,
          }),
        });
        if (res.ok) {
          const data: EncounterBalanceResponse = await res.json();
          this.lastBalancedResponse = data;
          this.tacticalSummary = data.tactical_summary;
          this.draftMonsters = data.monsters.map((m) => ({
            name: m.name,
            cr: m.cr,
            xp: m.xp,
            role: m.role,
            count: m.count,
          }));
          this.dispatchEvent(
            new CustomEvent('encounter-balanced', {
              detail: data,
              bubbles: true,
              composed: true,
            })
          );
        }
      }
    } catch {
      // Mock fallback
    } finally {
      this.loading = false;
    }
  }

  render() {
    const thresholds = this.computePartyThresholds();
    const totalMonsterCount = this.draftMonsters.reduce((acc, m) => acc + m.count, 0);
    const rawXp = this.draftMonsters.reduce((acc, m) => acc + m.xp * m.count, 0);
    const multiplier = this.computeMultiplier(totalMonsterCount, this.partyLevels.length);
    const adjustedXp = Math.floor(rawXp * multiplier);
    const lethality = this.getLethalityTier(adjustedXp, thresholds);

    return html`
      <div class="section-panel">
        <div class="builder-layout">
          <!-- Left Column: Party Setup & Thresholds -->
          <div class="roster-card">
            <h3 style="margin: 0; font-size: 1.05rem; font-weight: 800; text-transform: uppercase;">
              Party Roster & XP Thresholds
            </h3>

            <div>
              <div style="display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 700;">
                <span>Party Size: ${this.partyLevels.length} Adventurers</span>
              </div>
              <input
                type="range"
                min="1"
                max="8"
                .value=${String(this.partyLevels.length)}
                @input=${(e: Event) => this.setPartySize(Number((e.target as HTMLInputElement).value))}
                style="width: 100%;"
              />
            </div>

            <div>
              <div style="display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 700;">
                <span>Party Level: Level ${this.partyLevels[0] || 1}</span>
              </div>
              <input
                type="range"
                min="1"
                max="20"
                .value=${String(this.partyLevels[0] || 1)}
                @input=${(e: Event) => this.setPartyLevel(Number((e.target as HTMLInputElement).value))}
                style="width: 100%;"
              />
            </div>

            <div class="threshold-bar">
              <div class="threshold-item easy">Easy<br /><strong>${thresholds.easy} XP</strong></div>
              <div class="threshold-item medium">Med<br /><strong>${thresholds.medium} XP</strong></div>
              <div class="threshold-item hard">Hard<br /><strong>${thresholds.hard} XP</strong></div>
              <div class="threshold-item deadly">Deadly<br /><strong>${thresholds.deadly} XP</strong></div>
            </div>

            <div style="display: flex; flex-direction: column; gap: 4px;">
              <span style="font-size: 0.75rem; font-weight: 800; text-transform: uppercase;">Target Difficulty</span>
              <div style="display: flex; gap: 4px;">
                ${(['Easy', 'Medium', 'Hard', 'Deadly'] as DifficultyTier[]).map(
                  (diff) => html`
                    <button
                      class="small-btn ${this.targetDifficulty === diff ? 'add' : ''}"
                      style="flex: 1;"
                      @click=${() => {
                        this.targetDifficulty = diff;
                        this.requestUpdate();
                      }}
                    >
                      ${diff}
                    </button>
                  `
                )}
              </div>
            </div>

            <button
              class="action-btn primary"
              style="margin-top: 8px;"
              @click=${this.autoBalanceEncounter}
            >
              ${this.loading ? 'Balancing Encounter...' : '⚡ Auto-Balance Encounter'}
            </button>
          </div>

          <!-- Right Column: Combatant Roster & Lethality Gauge -->
          <div class="roster-card">
            <h3 style="margin: 0; font-size: 1.05rem; font-weight: 800; text-transform: uppercase;">
              Encounter Lethality & Roster
            </h3>

            <div class="lethality-status-box ${lethality}">
              ${lethality.toUpperCase()} (${adjustedXp} Adjusted XP / ${multiplier}x)
            </div>

            <div style="font-size: 0.78rem; display: flex; justify-content: space-between; font-weight: 700; color: #444;">
              <span>Total Monsters: ${totalMonsterCount}</span>
              <span>Raw XP: ${rawXp}</span>
              <span>Multiplier: ${multiplier}x</span>
            </div>

            <div class="draft-monster-list">
              ${this.draftMonsters.length === 0
                ? html`<div style="text-align: center; color: #666; font-size: 0.8rem; padding: 12px;">
                    No creatures in draft. Use Rule Search or Auto-Balance to draft enemies.
                  </div>`
                : this.draftMonsters.map(
                    (m) => html`
                      <div class="draft-monster-item">
                        <div>
                          <strong>${m.name}</strong>
                          <span style="font-size: 0.75rem; color: #666;"> (CR ${m.cr}, ${m.role})</span>
                          <div style="font-size: 0.72rem; color: #444;">${m.xp * m.count} XP (${m.xp} ea)</div>
                        </div>
                        <div class="qty-controls">
                          <button class="qty-btn" @click=${() => this.removeMonster(m.name)}>-</button>
                          <span style="font-size: 0.85rem; font-weight: 800; width: 18px; text-align: center;">
                            ${m.count}
                          </span>
                          <button class="qty-btn" @click=${() => this.addMonster(m)}>+</button>
                        </div>
                      </div>
                    `
                  )}
            </div>

            ${this.tacticalSummary
              ? html`
                  <div style="font-size: 0.78rem; background: #e2eafc; padding: 8px; border: 1px solid #121212;">
                    <strong>Tactical Strategy:</strong> ${this.tacticalSummary}
                  </div>
                `
              : ''}
          </div>
        </div>
      </div>
    `;
  }
}
