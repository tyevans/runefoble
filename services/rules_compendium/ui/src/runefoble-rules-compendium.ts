/**
 * Lit Web Component: <runefoble-rules-compendium>
 * Root Microfrontend for TTRPG Rules Compendium and CR Encounter Builder.
 * Governed by ADR-0001, ADR-0003, ADR-0004, ADR-0007, and ADR-0013.
 */

import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { compendiumStyles } from './runefoble-rules-compendium.styles.ts';
import './runefoble-rules-lookup.ts';
import './runefoble-encounter-builder.ts';
import type {
  DifficultyTier,
  DraftMonsterEntry,
  HomebrewCreateRequest,
  HomebrewResponse,
} from './types.ts';

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

  // Homebrew Form State
  @state() private hbRuleType: 'monster' | 'spell' | 'condition' = 'monster';
  @state() private hbTitle = '';
  @state() private hbCr = 1.0;
  @state() private hbCreatureType = 'fiend';
  @state() private hbAc = 15;
  @state() private hbHp = 30;
  @state() private hbXp = 200;
  @state() private hbRole = 'skirmisher';
  @state() private hbDescription = '';
  @state() private hbSubmitting = false;
  @state() private hbMessage = '';
  @state() private hbError = '';

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

  public async submitHomebrew(e: Event) {
    e.preventDefault();
    if (!this.hbTitle.trim()) {
      this.hbError = 'Rule title is required';
      return;
    }
    if (!this.campaignId) {
      this.hbError = 'Campaign ID required for homebrew';
      return;
    }

    this.hbSubmitting = true;
    this.hbMessage = '';
    this.hbError = '';

    const content: Record<string, any> =
      this.hbRuleType === 'monster'
        ? {
            challenge_rating: this.hbCr,
            creature_type: this.hbCreatureType,
            armor_class: this.hbAc,
            hit_points: this.hbHp,
            xp: this.hbXp,
            role: this.hbRole,
            description: this.hbDescription,
          }
        : {
            description: this.hbDescription,
          };

    const payload: HomebrewCreateRequest = {
      campaign_id: this.campaignId,
      rule_type: this.hbRuleType,
      title: this.hbTitle,
      content,
    };

    try {
      if (this.apiBaseUrl) {
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
        };
        if (this.userId) {
          headers['x-user-id'] = this.userId;
        }

        const res = await fetch(`${this.apiBaseUrl}/api/v1/compendium/homebrew`, {
          method: 'POST',
          headers,
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({ detail: 'Registration failed' }));
          this.hbError = errData.detail || `Server error (${res.status})`;
          return;
        }

        const data: HomebrewResponse = await res.json();
        this.hbMessage = `Registered "${data.title}" successfully!`;
        this.dispatchEvent(
          new CustomEvent('homebrew-created', {
            detail: data,
            bubbles: true,
            composed: true,
          })
        );
        // Reset form
        this.hbTitle = '';
        this.hbDescription = '';
      } else {
        this.hbMessage = `Homebrew rule "${this.hbTitle}" validated.`;
      }
    } catch (err: any) {
      this.hbError = err.message || 'Network error registering homebrew rule';
    } finally {
      this.hbSubmitting = false;
    }
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
      <div class="section-panel">
        <div class="roster-card">
          <h3 style="margin: 0; font-size: 1.1rem; font-weight: 800; text-transform: uppercase;">
            Author Campaign Homebrew Rule
          </h3>
          <p style="font-size: 0.8rem; color: #555; margin: 0;">
            Guarded by SpiceDB Zanzibar authorization. DM permissions required on campaign context.
          </p>

          ${this.hbMessage
            ? html`<div style="background: #d8f3dc; color: #1b4332; border: 1px solid #121212; padding: 8px; font-weight: 700; font-size: 0.85rem;">
                ${this.hbMessage}
              </div>`
            : ''}
          ${this.hbError
            ? html`<div style="background: #ffccd5; color: #800f2f; border: 1px solid #121212; padding: 8px; font-weight: 700; font-size: 0.85rem;">
                ${this.hbError}
              </div>`
            : ''}

          <form @submit=${this.submitHomebrew} style="display: flex; flex-direction: column; gap: 10px;">
            <div class="form-grid-2">
              <div class="form-group">
                <label class="form-label">Rule Type</label>
                <select
                  class="form-select"
                  .value=${this.hbRuleType}
                  @change=${(e: Event) =>
                    (this.hbRuleType = (e.target as HTMLSelectElement).value as any)}
                >
                  <option value="monster">Monster / NPC</option>
                  <option value="spell">Spell</option>
                  <option value="condition">Condition</option>
                </select>
              </div>

              <div class="form-group">
                <label class="form-label">Title / Name</label>
                <input
                  type="text"
                  class="form-input"
                  placeholder="e.g. Abyssal Stalker"
                  .value=${this.hbTitle}
                  @input=${(e: Event) => (this.hbTitle = (e.target as HTMLInputElement).value)}
                  required
                />
              </div>
            </div>

            ${this.hbRuleType === 'monster'
              ? html`
                  <div class="form-grid-2">
                    <div class="form-group">
                      <label class="form-label">Challenge Rating (CR)</label>
                      <input
                        type="number"
                        step="0.125"
                        min="0"
                        max="30"
                        class="form-input"
                        .value=${String(this.hbCr)}
                        @input=${(e: Event) =>
                          (this.hbCr = Number((e.target as HTMLInputElement).value))}
                      />
                    </div>
                    <div class="form-group">
                      <label class="form-label">XP Value</label>
                      <input
                        type="number"
                        min="0"
                        class="form-input"
                        .value=${String(this.hbXp)}
                        @input=${(e: Event) =>
                          (this.hbXp = Number((e.target as HTMLInputElement).value))}
                      />
                    </div>
                  </div>

                  <div class="form-grid-2">
                    <div class="form-group">
                      <label class="form-label">Armor Class (AC)</label>
                      <input
                        type="number"
                        min="1"
                        max="35"
                        class="form-input"
                        .value=${String(this.hbAc)}
                        @input=${(e: Event) =>
                          (this.hbAc = Number((e.target as HTMLInputElement).value))}
                      />
                    </div>
                    <div class="form-group">
                      <label class="form-label">Hit Points (HP)</label>
                      <input
                        type="number"
                        min="1"
                        class="form-input"
                        .value=${String(this.hbHp)}
                        @input=${(e: Event) =>
                          (this.hbHp = Number((e.target as HTMLInputElement).value))}
                      />
                    </div>
                  </div>

                  <div class="form-grid-2">
                    <div class="form-group">
                      <label class="form-label">Creature Type</label>
                      <input
                        type="text"
                        class="form-input"
                        .value=${this.hbCreatureType}
                        @input=${(e: Event) =>
                          (this.hbCreatureType = (e.target as HTMLInputElement).value)}
                      />
                    </div>
                    <div class="form-group">
                      <label class="form-label">Tactical Role</label>
                      <select
                        class="form-select"
                        .value=${this.hbRole}
                        @change=${(e: Event) =>
                          (this.hbRole = (e.target as HTMLSelectElement).value)}
                      >
                        <option value="skirmisher">Skirmisher</option>
                        <option value="brute">Brute</option>
                        <option value="controller">Controller</option>
                        <option value="artillery">Artillery</option>
                      </select>
                    </div>
                  </div>
                `
              : ''}

            <div class="form-group">
              <label class="form-label">Description / Rules Text</label>
              <textarea
                class="form-textarea"
                rows="3"
                placeholder="Mechanics, traits, spell details..."
                .value=${this.hbDescription}
                @input=${(e: Event) =>
                  (this.hbDescription = (e.target as HTMLTextAreaElement).value)}
              ></textarea>
            </div>

            <button
              type="submit"
              class="action-btn primary"
              style="align-self: flex-start; margin-top: 6px;"
              ?disabled=${this.hbSubmitting}
            >
              ${this.hbSubmitting ? 'Registering...' : 'Register Homebrew Rule'}
            </button>
          </form>
        </div>
      </div>
    `;
  }
}
