import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { espionageStyles } from './runefoble-faction-espionage.styles.ts';

export interface EspionageAlert {
  id: string;
  faction_id: string;
  faction_name: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  summary: string;
  region?: string;
  timestamp?: string;
}

export interface InterceptedDispatch {
  id: string;
  sender_faction: string;
  target_recipient: string;
  region: string;
  intercept_status: 'intercepted' | 'decrypted' | 'compromised';
  message_snippet: string;
  timestamp?: string;
}

export interface RegionalAlert {
  region_id: string;
  region_name: string;
  alert_level: 'normal' | 'elevated' | 'high' | 'lockdown';
  unrest_score: number;
}

@customElement('runefoble-faction-espionage')
export class RunefobleFactionEspionage extends LitElement {
  @property({ type: String }) campaignId = '';
  @property({ type: Array }) alerts: EspionageAlert[] = [];
  @property({ type: Array }) intercepts: InterceptedDispatch[] = [];
  @property({ type: Array }) regionalAlerts: RegionalAlert[] = [];
  @property({ type: String }) selectedId: string | null = null;
  @property({ type: String }) filterSeverity = 'all';
  @property({ type: Boolean }) isDm = false;

  static styles = espionageStyles;

  private handleSelectAlert(alert: EspionageAlert) {
    this.selectedId = alert.id;
    this.dispatchEvent(new CustomEvent('alert-selected', { detail: { alertId: alert.id, alert }, bubbles: true, composed: true }));
  }

  private handleSelectDispatch(dispatch: InterceptedDispatch) {
    this.selectedId = dispatch.id;
    this.dispatchEvent(new CustomEvent('dispatch-inspected', { detail: { dispatchId: dispatch.id, dispatch }, bubbles: true, composed: true }));
  }

  private handleSetFilter(filter: string) {
    this.filterSeverity = filter;
    this.dispatchEvent(new CustomEvent('filter-changed', { detail: { filter }, bubbles: true, composed: true }));
  }

  private getFilteredAlerts(): EspionageAlert[] {
    if (this.filterSeverity === 'all') return this.alerts;
    return this.alerts.filter((a) => a.severity === this.filterSeverity);
  }

  render() {
    const alerts = this.getFilteredAlerts();
    return html`
      <div class="container">
        <div class="header">
          <div class="title-group">
            <h2 class="title">Faction Espionage & Alert Feed</h2>
            ${this.campaignId ? html`<span class="campaign-tag">${this.campaignId}</span>` : ''}
          </div>
          <div class="filters">
            ${['all', 'critical', 'high', 'medium'].map((f) => html`
              <button class="filter-btn ${this.filterSeverity === f ? 'active' : ''}" @click=${() => this.handleSetFilter(f)}>${f}</button>
            `)}
          </div>
        </div>

        ${this.regionalAlerts.length > 0 ? html`
          <div class="section-title">Regional Security Posture</div>
          <div class="regional-grid">
            ${this.regionalAlerts.map((r) => html`
              <div class="region-chip">
                <span class="region-name">${r.region_name}</span>
                <span class="badge ${r.alert_level === 'lockdown' ? 'badge-critical' : r.alert_level === 'high' ? 'badge-high' : 'badge-medium'}">${r.alert_level} (${r.unrest_score}%)</span>
              </div>
            `)}
          </div>
        ` : ''}

        <div class="section-title">Active Espionage Alerts (${alerts.length})</div>
        ${alerts.length === 0 ? html`<div class="empty-state">No clandestine operations reported for current filter.</div>` : html`
          <div class="card-list">
            ${alerts.map((a) => html`
              <div class="card ${this.selectedId === a.id ? 'selected' : ''}" @click=${() => this.handleSelectAlert(a)}>
                <div class="card-header">
                  <span class="card-title">${a.title}</span>
                  <span class="badge badge-${a.severity}">${a.severity}</span>
                </div>
                <div class="card-meta">${a.faction_name}${a.region ? ` · ${a.region}` : ''}${a.timestamp ? ` · ${a.timestamp}` : ''}</div>
                <p class="card-summary">${a.summary}</p>
                ${this.selectedId === a.id ? html`
                  <div class="dossier-panel">
                    <strong>DOSSIER INTEL:</strong> Source verified. Faction: ${a.faction_id}. Security risk confirmed.
                    ${this.isDm ? html`<div><em>[DM Confidential: Informant ID covert-007, risk vector critical]</em></div>` : ''}
                  </div>
                ` : ''}
              </div>
            `)}
          </div>
        `}

        ${this.intercepts.length > 0 ? html`
          <div class="section-title">Intercepted Courier Dispatches (${this.intercepts.length})</div>
          <div class="card-list">
            ${this.intercepts.map((d) => html`
              <div class="card ${this.selectedId === d.id ? 'selected' : ''}" @click=${() => this.handleSelectDispatch(d)}>
                <div class="card-header">
                  <span class="card-title">${d.sender_faction} ➔ ${d.target_recipient}</span>
                  <span class="badge ${d.intercept_status === 'compromised' ? 'badge-critical' : 'badge-medium'}">${d.intercept_status}</span>
                </div>
                <div class="card-meta">Route: ${d.region}${d.timestamp ? ` · ${d.timestamp}` : ''}</div>
                <p class="card-summary">"${d.message_snippet}"</p>
                ${this.selectedId === d.id ? html`
                  <div class="dossier-panel">
                    <strong>COURIER TRANSCRIPT:</strong> Decryption verified. Transmitted across ${d.region}.
                  </div>
                ` : ''}
              </div>
            `)}
          </div>
        ` : ''}
      </div>
    `;
  }
}
