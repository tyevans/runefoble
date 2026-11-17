/**
 * Lit Web Component: <runefoble-campaign-analytics>
 * Governed by ADR-0004, ADR-0007, ADR-0011, and ADR-0013.
 */

import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { campaignAnalyticsStyles } from './runefoble-campaign-analytics.styles.ts';
import './runefoble-combat-heatmap.ts';
import './runefoble-chronicle-timeline.ts';
import type {
  CampaignHeatmapResponse,
  CampaignMvpResponse,
  CampaignTimelineResponse,
  CombatantPerformance,
} from './types.ts';

/**
 * Renders campaign telemetry. The host loads the three datasets through its authenticated
 * data layer and passes them in. This element performs no network calls (TASK-0646).
 */
@customElement('runefoble-campaign-analytics')
export class RunefobleCampaignAnalytics extends LitElement {
  static styles = [campaignAnalyticsStyles];

  @property({ type: String }) campaignId = 'campaign-1';
  @property({ type: String }) sessionId: string | null = null;
  @property({ type: String }) encounterId: string | null = null;
  @property({ type: String }) activeTab: 'all' | 'heatmap' | 'performance' | 'timeline' = 'all';

  @property({ type: Object }) heatmapData: CampaignHeatmapResponse | null = null;
  @property({ type: Object }) mvpData: CampaignMvpResponse | null = null;
  @property({ type: Object }) timelineData: CampaignTimelineResponse | null = null;

  @state() private selectedMilestoneIndex = 0;

  private handleTabSelect(tab: 'all' | 'heatmap' | 'performance' | 'timeline') {
    this.activeTab = tab;
    this.dispatchEvent(
      new CustomEvent('tab-changed', {
        detail: { tab },
        bubbles: true,
        composed: true,
      })
    );
  }

  private renderPerformanceSection() {
    const mvp = this.mvpData;
    const combatants = mvp?.combatants || [];
    const maxVal = Math.max(
      ...combatants.map((c) => Math.max(c.damage_dealt, c.damage_taken, c.healing_provided)),
      1
    );

    return html`
      <div class="section-panel">
        <div class="section-title">
          <span>Party Performance & Tactical Infographics</span>
          <span>${combatants.length} Combatants</span>
        </div>

        ${mvp?.overall_mvp
          ? html`
              <div class="mvp-banner">
                <div class="mvp-banner-left">
                  <div class="mvp-trophy">🏆</div>
                  <div>
                    <div class="mvp-banner-title">${mvp.overall_mvp.title}</div>
                    <div class="mvp-recipient-name">${mvp.overall_mvp.recipient_name}</div>
                    <div style="font-size: 0.75rem; color: #555;">${mvp.overall_mvp.description}</div>
                  </div>
                </div>
                <div class="mvp-banner-score">Score: ${mvp.overall_mvp.score}</div>
              </div>
            `
          : ''}
        ${mvp?.awards?.length
          ? html`
              <div class="awards-grid">
                ${mvp.awards.map(
                  (award) => html`
                    <div class="award-badge-card">
                      <div class="award-badge-title">${award.title}</div>
                      <div class="award-recipient">${award.recipient_name}</div>
                      <div class="award-desc">${award.description}</div>
                    </div>
                  `
                )}
              </div>
            `
          : ''}

        <div class="chart-container">
          <div class="chart-legend">
            <span><span class="legend-dot" style="background: var(--rf-accent-primary, #e63946);"></span>Damage Dealt</span>
            <span><span class="legend-dot" style="background: #d4a373;"></span>Damage Sustained</span>
            <span><span class="legend-dot" style="background: var(--rf-accent-secondary, #2a9d8f);"></span>Healing Output</span>
          </div>

          ${combatants.map(
            (c: CombatantPerformance) => html`
              <div class="chart-row">
                <div class="chart-row-header">
                  <span>${c.combatant_name} (Turns: ${c.turns_taken}, Crits: ${c.critical_hits})</span>
                  <span>Dealt: ${c.damage_dealt} | Taken: ${c.damage_taken} | Healed: ${c.healing_provided}</span>
                </div>
                <div class="chart-bar-container">
                  <div class="bar-dealt" style="width: ${(c.damage_dealt / maxVal) * 50}%" title="Dealt: ${c.damage_dealt}"></div>
                  <div class="bar-taken" style="width: ${(c.damage_taken / maxVal) * 30}%" title="Taken: ${c.damage_taken}"></div>
                  <div class="bar-healing" style="width: ${(c.healing_provided / maxVal) * 20}%" title="Healed: ${c.healing_provided}"></div>
                </div>
              </div>
            `
          )}
        </div>
      </div>
    `;
  }

  render() {
    const totalDmg = this.mvpData?.combatants.reduce((acc, c) => acc + c.damage_dealt, 0) || 0;
    const totalStrikes = this.heatmapData?.cells.reduce((acc, c) => acc + c.hit_count, 0) || 0;
    const totalKnockouts = this.heatmapData?.cells.reduce((acc, c) => acc + c.knockout_count, 0) || 0;
    const totalMilestones = this.timelineData?.total_milestones || this.timelineData?.milestones.length || 0;

    return html`
      <div class="analytics-header">
        <div class="title-group">
          <div class="main-title">
            <span>Campaign Telemetry & Chronicle</span>
          </div>
          <div class="campaign-meta">
            <span>Campaign: <strong>${this.campaignId}</strong></span>
            ${this.sessionId ? html`<span>Session: <strong>${this.sessionId}</strong></span>` : ''}
            ${this.encounterId ? html`<span>Encounter: <strong>${this.encounterId}</strong></span>` : ''}
          </div>
        </div>

        <div class="tabs-nav">
          <button
            class="tab-btn ${this.activeTab === 'all' ? 'active' : ''}"
            @click=${() => this.handleTabSelect('all')}
          >
            Overview
          </button>
          <button
            class="tab-btn ${this.activeTab === 'heatmap' ? 'active' : ''}"
            @click=${() => this.handleTabSelect('heatmap')}
          >
            Spatial Heatmap
          </button>
          <button
            class="tab-btn ${this.activeTab === 'performance' ? 'active' : ''}"
            @click=${() => this.handleTabSelect('performance')}
          >
            Performance & MVP
          </button>
          <button
            class="tab-btn ${this.activeTab === 'timeline' ? 'active' : ''}"
            @click=${() => this.handleTabSelect('timeline')}
          >
            Chronicle Timeline
          </button>
        </div>
      </div>

      <div class="summary-metrics-row">
        <div class="metric-card">
          <span class="metric-label">Total Damage</span>
          <span class="metric-value">${totalDmg}</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">Strikes Landed</span>
          <span class="metric-value">${totalStrikes}</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">Knockouts</span>
          <span class="metric-value">${totalKnockouts}</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">Chronicle Milestones</span>
          <span class="metric-value">${totalMilestones}</span>
        </div>
      </div>

      ${this.activeTab === 'all'
        ? html`
            <div class="dashboard-grid">
              <runefoble-combat-heatmap
                .heatmapData=${this.heatmapData}
              ></runefoble-combat-heatmap>
              <runefoble-chronicle-timeline
                .timelineData=${this.timelineData}
                .activeIndex=${this.selectedMilestoneIndex}
                @milestone-selected=${(e: CustomEvent) => (this.selectedMilestoneIndex = e.detail.index)}
              ></runefoble-chronicle-timeline>
            </div>
            <div style="margin-top: 20px;">
              ${this.renderPerformanceSection()}
            </div>
          `
        : ''}

      ${this.activeTab === 'heatmap'
        ? html`
            <runefoble-combat-heatmap
              .heatmapData=${this.heatmapData}
            ></runefoble-combat-heatmap>
          `
        : ''}

      ${this.activeTab === 'performance' ? this.renderPerformanceSection() : ''}

      ${this.activeTab === 'timeline'
        ? html`
            <runefoble-chronicle-timeline
              .timelineData=${this.timelineData}
              .activeIndex=${this.selectedMilestoneIndex}
              @milestone-selected=${(e: CustomEvent) => (this.selectedMilestoneIndex = e.detail.index)}
            ></runefoble-chronicle-timeline>
          `
        : ''}
    `;
  }
}
