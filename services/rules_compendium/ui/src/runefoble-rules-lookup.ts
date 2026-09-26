/**
 * Lit Web Component: <runefoble-rules-lookup>
 * Governed by ADR-0004, ADR-0007, and ADR-0013.
 */

import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { compendiumStyles } from './runefoble-rules-compendium.styles.ts';
import type { RuleCategory, RuleSearchResultItem, RuleSearchResponse } from './types.ts';

@customElement('runefoble-rules-lookup')
export class RunefobleRulesLookup extends LitElement {
  static styles = [compendiumStyles];

  @property({ type: String }) apiBaseUrl = '';
  @property({ type: String }) campaignId: string | null = null;
  @property({ type: String }) userId: string | null = null;
  @property({ type: String }) selectedCategory: RuleCategory = 'all';
  @property({ type: Array }) results: RuleSearchResultItem[] = [];
  @property({ type: Number }) tookMs = 0;
  @property({ type: Boolean }) enableAddToEncounter = true;

  @state() searchQuery = '';
  @state() loading = false;
  @state() expandedRule: RuleSearchResultItem | null = null;
  private debounceTimer: number | null = null;

  firstUpdated() {
    if (this.results.length === 0 && this.apiBaseUrl) {
      this.executeSearch('goblin');
    }
  }

  private handleSearchInput(e: Event) {
    this.searchQuery = (e.target as HTMLInputElement).value;
    if (this.debounceTimer) clearTimeout(this.debounceTimer);
    this.debounceTimer = window.setTimeout(() => {
      this.executeSearch(this.searchQuery);
    }, 200);
  }

  public async executeSearch(query: string) {
    if (!query || !query.trim()) {
      if (!this.apiBaseUrl) return;
      query = 'fire';
    }
    this.loading = true;

    try {
      const catParam =
        this.selectedCategory !== 'all' && this.selectedCategory !== 'homebrew'
          ? `&category=${this.selectedCategory}`
          : '';
      const campParam = this.campaignId ? `&campaign_id=${this.campaignId}` : '';
      const url = `${this.apiBaseUrl}/api/v1/compendium/rules/search?query=${encodeURIComponent(query)}${catParam}${campParam}`;

      const headers: Record<string, string> = {};
      if (this.userId) {
        headers['x-user-id'] = this.userId;
      }

      const res = await fetch(url, { headers });
      if (res.ok) {
        const data: RuleSearchResponse = await res.json();
        this.results = data.results;
        this.tookMs = data.took_ms;
        this.dispatchEvent(
          new CustomEvent('search-completed', {
            detail: data,
            bubbles: true,
            composed: true,
          })
        );
      }
    } catch {
      // Local fallback or demo state
    } finally {
      this.loading = false;
    }
  }

  private setCategory(cat: RuleCategory) {
    this.selectedCategory = cat;
    this.executeSearch(this.searchQuery);
  }

  private handleInspect(rule: RuleSearchResultItem) {
    this.expandedRule = this.expandedRule?.name === rule.name ? null : rule;
    this.dispatchEvent(
      new CustomEvent('rule-selected', {
        detail: { rule },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleAddMonster(rule: RuleSearchResultItem) {
    this.dispatchEvent(
      new CustomEvent('monster-added', {
        detail: {
          monster: {
            name: rule.name,
            cr: rule.details.challenge_rating ?? 1,
            xp: rule.details.xp ?? 200,
            role: rule.details.role ?? 'skirmisher',
            count: 1,
          },
        },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    const filteredResults =
      this.selectedCategory === 'homebrew'
        ? this.results.filter((r) => r.is_homebrew)
        : this.results;

    return html`
      <div class="section-panel">
        <div class="search-bar-row">
          <input
            type="text"
            class="search-input"
            placeholder="Search monsters, spells, conditions (e.g. Fireball, Goblin)..."
            .value=${this.searchQuery}
            @input=${this.handleSearchInput}
            @keydown=${(e: KeyboardEvent) => e.key === 'Enter' && this.executeSearch(this.searchQuery)}
          />
          <button
            class="action-btn primary"
            @click=${() => this.executeSearch(this.searchQuery)}
          >
            ${this.loading ? 'Searching...' : 'Search'}
          </button>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
          <div class="filter-pills">
            ${(['all', 'monster', 'spell', 'condition', 'homebrew'] as RuleCategory[]).map(
              (cat) => html`
                <button
                  class="filter-pill ${this.selectedCategory === cat ? 'active' : ''}"
                  @click=${() => this.setCategory(cat)}
                >
                  ${cat.toUpperCase()}
                </button>
              `
            )}
          </div>
          ${this.tookMs > 0
            ? html`<span class="latency-badge">⚡ ${this.tookMs.toFixed(1)}ms (Sub-50ms SLA)</span>`
            : ''}
        </div>

        ${this.expandedRule ? this.renderExpandedDetails(this.expandedRule) : ''}

        <div class="results-grid">
          ${filteredResults.length === 0
            ? html`<div style="grid-column: 1 / -1; padding: 24px; text-align: center; color: #666; font-size: 0.85rem;">
                No compendium entries found matching query.
              </div>`
            : filteredResults.map((rule) => this.renderResultCard(rule))}
        </div>
      </div>
    `;
  }

  private renderResultCard(rule: RuleSearchResultItem) {
    const isMonster = rule.category === 'monster';
    return html`
      <div class="result-card">
        <div class="card-top">
          <h3 class="rule-title">${rule.name}</h3>
          <span class="category-tag ${rule.category}">
            ${rule.is_homebrew ? '★ Homebrew' : rule.category}
          </span>
        </div>

        <div class="summary-text">${rule.summary}</div>

        <div class="details-bar">
          ${rule.category === 'monster'
            ? html`
                <span>CR: ${rule.details.challenge_rating ?? '—'}</span>
                <span>XP: ${rule.details.xp ?? '—'}</span>
                <span>Role: ${rule.details.role ?? '—'}</span>
              `
            : rule.category === 'spell'
              ? html`
                  <span>Lvl: ${rule.details.level ?? 'Cantrip'}</span>
                  <span>${rule.details.school ?? 'Magic'}</span>
                `
              : html`<span>Condition Effects: ${rule.details.effects?.length ?? 1}</span>`}
        </div>

        <div class="card-footer">
          <button class="small-btn" @click=${() => this.handleInspect(rule)}>
            ${this.expandedRule?.name === rule.name ? 'Hide' : 'Inspect'}
          </button>
          ${isMonster && this.enableAddToEncounter
            ? html`
                <button class="small-btn add" @click=${() => this.handleAddMonster(rule)}>
                  + Add to CR Builder
                </button>
              `
            : ''}
        </div>
      </div>
    `;
  }

  private renderExpandedDetails(rule: RuleSearchResultItem) {
    const stats = rule.details.stats || {};
    return html`
      <div class="stat-block-expanded">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <h4 style="margin: 0; font-size: 1.1rem; font-weight: 800;">
            ${rule.name}
            <span style="font-size: 0.75rem; font-weight: 600; color: #555;">
              (${rule.details.size || ''} ${rule.details.creature_type || rule.category})
            </span>
          </h4>
          <button class="small-btn" @click=${() => (this.expandedRule = null)}>Close</button>
        </div>

        ${rule.category === 'monster'
          ? html`
              <div class="stat-grid">
                <div><div class="stat-cell-title">STR</div><div class="stat-cell-val">${stats.STR ?? 10}</div></div>
                <div><div class="stat-cell-title">DEX</div><div class="stat-cell-val">${stats.DEX ?? 10}</div></div>
                <div><div class="stat-cell-title">CON</div><div class="stat-cell-val">${stats.CON ?? 10}</div></div>
                <div><div class="stat-cell-title">INT</div><div class="stat-cell-val">${stats.INT ?? 10}</div></div>
                <div><div class="stat-cell-title">WIS</div><div class="stat-cell-val">${stats.WIS ?? 10}</div></div>
                <div><div class="stat-cell-title">CHA</div><div class="stat-cell-val">${stats.CHA ?? 10}</div></div>
              </div>
              <div style="font-size: 0.8rem; display: flex; gap: 12px; font-weight: 700;">
                <span>Armor Class: ${rule.details.armor_class ?? 10}</span>
                <span>Hit Points: ${rule.details.hit_points ?? 10}</span>
                <span>Speed: ${rule.details.speed ?? '30 ft.'}</span>
              </div>
            `
          : ''}

        <div style="font-size: 0.82rem; line-height: 1.4;">
          ${rule.details.description || rule.summary}
        </div>
      </div>
    `;
  }
}
