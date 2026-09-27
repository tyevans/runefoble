import { LitElement, html, svg } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { factionRadarStyles } from './runefoble-faction-radar.styles.ts';

export interface FactionShift {
  tick?: number;
  description: string;
  type?: string;
  timestamp?: string;
}

export interface FactionData {
  faction_id: string;
  campaign_id?: string;
  name: string;
  influence: number;
  resources: number;
  disposition: string;
  active_goal: string;
  goal_progress: number;
  goal_target: number;
  rival_faction_ids?: string[];
  territory?: string;
  shifts?: FactionShift[];
  history?: Array<Record<string, unknown>>;
}

export interface GeopoliticalShift {
  faction_id: string;
  faction_name: string;
  territory: string;
  shift_type: string;
  description: string;
  severity: string;
  ripple_effects: string[];
}

export interface WorldTickData {
  campaign_id: string;
  tick_number: number;
  intelligence_bulletin: string;
  factions?: FactionData[];
  shifts?: GeopoliticalShift[];
  tavern_rumors?: string[];
  timestamp: string;
}

@customElement('runefoble-faction-radar')
export class RunefobleFactionRadar extends LitElement {
  @property({ type: String }) campaignId = '';
  @property({ type: Array }) factions: FactionData[] = [];
  @property({ type: Object }) bulletin: WorldTickData | null = null;
  @property({ type: Boolean }) isDm = false;
  @property({ type: String }) selectedFactionId = '';
  @property({ type: Boolean }) isDrawerOpen = false;
  @property({ type: Array }) tavernRumors: string[] = [];

  static styles = factionRadarStyles;

  private selectFaction(faction: FactionData) {
    this.selectedFactionId = faction.faction_id;
    this.dispatchEvent(
      new CustomEvent('faction-selected', {
        detail: { factionId: faction.faction_id, faction },
        bubbles: true,
        composed: true,
      })
    );
  }

  private toggleDrawer() {
    this.isDrawerOpen = !this.isDrawerOpen;
    this.dispatchEvent(
      new CustomEvent('drawer-toggled', {
        detail: { isOpen: this.isDrawerOpen },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleTriggerWorldTick() {
    this.dispatchEvent(
      new CustomEvent('world-tick-requested', {
        detail: { campaignId: this.campaignId },
        bubbles: true,
        composed: true,
      })
    );
  }

  private getRumorsList(): string[] {
    if (this.tavernRumors?.length) return this.tavernRumors;
    if (this.bulletin?.tavern_rumors?.length) return this.bulletin.tavern_rumors;
    return [];
  }

  private renderRadarChart() {
    const list = this.factions.length > 0 ? this.factions : (this.bulletin?.factions || []);
    if (list.length < 3) {
      return html`
        <div class="radar-card">
          <div class="radar-title">Influence Gauge Matrix</div>
          <div class="empty-state">
            ${list.length === 0
              ? 'No factions registered in campaign.'
              : `${list.length} faction(s) monitored (radar requires 3+ for polygon projection).`}
          </div>
        </div>
      `;
    }

    const cx = 150;
    const cy = 150;
    const radius = 100;
    const numPoints = list.length;
    const angleStep = (2 * Math.PI) / numPoints;
    const rings = [0.25, 0.5, 0.75, 1.0];

    const axes = list.map((f, i) => {
      const angle = -Math.PI / 2 + i * angleStep;
      return {
        faction: f,
        x: cx + radius * Math.cos(angle),
        y: cy + radius * Math.sin(angle),
        labelX: cx + (radius + 20) * Math.cos(angle),
        labelY: cy + (radius + 20) * Math.sin(angle) + 4,
      };
    });

    const polygonPoints = list
      .map((f, i) => {
        const inf = Math.max(5, Math.min(100, f.influence));
        const r = (inf / 100) * radius;
        const angle = -Math.PI / 2 + i * angleStep;
        return `${(cx + r * Math.cos(angle)).toFixed(1)},${(cy + r * Math.sin(angle)).toFixed(1)}`;
      })
      .join(' ');

    return html`
      <div class="radar-card">
        <div class="radar-title">Geopolitical Influence Radar</div>
        <svg class="radar-svg" viewBox="0 0 300 300">
          ${rings.map(
            (scale) => svg`
              <circle class="radar-ring" cx="${cx}" cy="${cy}" r="${(radius * scale).toFixed(1)}" />
            `
          )}
          ${axes.map(
            (axis) => svg`
              <line class="radar-axis-line" x1="${cx}" y1="${cy}" x2="${axis.x.toFixed(1)}" y2="${axis.y.toFixed(1)}" />
              <text class="radar-label" x="${axis.labelX.toFixed(1)}" y="${axis.labelY.toFixed(1)}">
                ${axis.faction.name.slice(0, 10)}
              </text>
            `
          )}
          <polygon class="radar-polygon" points="${polygonPoints}" />
          ${list.map((f, i) => {
            const inf = Math.max(5, Math.min(100, f.influence));
            const r = (inf / 100) * radius;
            const angle = -Math.PI / 2 + i * angleStep;
            const isSelected = this.selectedFactionId === f.faction_id;
            return svg`
              <circle
                class="radar-node ${isSelected ? 'selected' : ''}"
                cx="${(cx + r * Math.cos(angle)).toFixed(1)}"
                cy="${(cy + r * Math.sin(angle)).toFixed(1)}"
                r="${isSelected ? 6 : 4}"
                @click="${() => this.selectFaction(f)}"
              >
                <title>${f.name}: ${f.influence}% Influence</title>
              </circle>
            `;
          })}
        </svg>
      </div>
    `;
  }

  private renderFactionCards() {
    const list = this.factions.length > 0 ? this.factions : (this.bulletin?.factions || []);
    if (list.length === 0) {
      return html`<div class="empty-state">No factions available</div>`;
    }

    return html`
      <div class="factions-roster">
        ${list.map((f) => {
          const isSelected = this.selectedFactionId === f.faction_id;
          const disp = f.disposition.toLowerCase();
          const goalPct = Math.min(100, Math.round((f.goal_progress / (f.goal_target || 100)) * 100));
          return html`
            <div class="faction-card ${isSelected ? 'selected' : ''}" @click="${() => this.selectFaction(f)}">
              <div class="faction-header">
                <span class="faction-name">${f.name}</span>
                <span class="disposition-badge disposition-${disp}">${f.disposition}</span>
              </div>
              <div class="faction-meta">
                ${f.territory ? html`<span class="chip-territory">📍 ${f.territory}</span>` : ''}
              </div>
              <div class="metrics-row">
                <div class="metric-bar-group">
                  <div class="metric-label"><span>Influence</span><span>${f.influence}/100</span></div>
                  <div class="progress-track"><div class="progress-fill" style="width: ${f.influence}%"></div></div>
                </div>
                <div class="metric-bar-group">
                  <div class="metric-label"><span>Resources</span><span>${f.resources}/100</span></div>
                  <div class="progress-track"><div class="progress-fill resources" style="width: ${f.resources}%"></div></div>
                </div>
              </div>
              ${f.active_goal
                ? html`
                    <div class="faction-goal">
                      <strong>Agenda:</strong> ${f.active_goal} (${goalPct}%)
                      <div class="progress-track" style="margin-top: 4px">
                        <div class="progress-fill goal" style="width: ${goalPct}%"></div>
                      </div>
                    </div>
                  `
                : ''}
            </div>
          `;
        })}
      </div>
    `;
  }

  private renderDmDrawer() {
    if (!this.isDrawerOpen) return null;
    if (!this.isDm) {
      return html`
        <div class="redacted-box">
          🔒 Classified: SpiceDB Zanzibar Redaction Active.<br />
          Private DM intelligence briefings and background tactical moves are hidden from players.
        </div>
      `;
    }

    const shifts = this.bulletin?.shifts || [];
    const bulletinText = this.bulletin?.intelligence_bulletin || '';

    return html`
      <div class="dm-drawer">
        <div class="drawer-header">
          <div class="drawer-title"><span>👁️ The Watcher Secret DM Briefing</span></div>
          <button class="btn" @click="${this.toggleDrawer}">Close</button>
        </div>
        ${bulletinText
          ? html`<div class="bulletin-content">${bulletinText}</div>`
          : html`<div class="empty-state">No raw bulletin generated for this tick.</div>`}
        ${shifts.length > 0
          ? html`
              <div class="radar-title" style="margin-top: 10px">Geopolitical Shifts & Ripple Effects</div>
              <div class="shifts-list">
                ${shifts.map(
                  (s) => html`
                    <div class="shift-card">
                      <div class="shift-card-header">
                        <span><strong>${s.faction_name}</strong> - ${s.shift_type.toUpperCase()}</span>
                        <span class="severity-badge severity-${s.severity}">${s.severity}</span>
                      </div>
                      <div style="font-size: 0.8rem; margin: 4px 0">${s.description}</div>
                      <div class="chip-territory" style="display: inline-block; margin-bottom: 4px">
                        Territory: ${s.territory}
                      </div>
                      ${s.ripple_effects?.length
                        ? html`
                            <div class="ripple-tags">
                              ${s.ripple_effects.map((r) => html`<span class="ripple-tag">⚡ ${r}</span>`)}
                            </div>
                          `
                        : ''}
                    </div>
                  `
                )}
              </div>
            `
          : ''}
      </div>
    `;
  }

  private renderRumors() {
    const rumors = this.getRumorsList();
    return html`
      <div class="rumors-section">
        <div class="rumors-header">
          <span>🍻</span>
          <h4>Public Tavern Rumors & Street Whispers</h4>
        </div>
        ${rumors.length === 0
          ? html`<div class="empty-state">No tavern rumors currently circulating.</div>`
          : html`
              <div class="rumors-list">
                ${rumors.map((r) => html`<div class="rumor-item">"${r}"</div>`)}
              </div>
            `}
      </div>
    `;
  }

  render() {
    const tickNum = this.bulletin?.tick_number ?? 0;
    return html`
      <div class="header">
        <div class="title-group">
          <h3>Autonomous NPC Faction Radar</h3>
          <span class="badge badge-tick">${tickNum > 0 ? `Tick #${tickNum}` : 'Standby'}</span>
          <span class="badge ${this.isDm ? 'badge-dm' : 'badge-player'}">
            ${this.isDm ? 'DM Clearance' : 'Player View'}
          </span>
        </div>
        <div class="controls-group">
          ${this.isDm
            ? html`<button class="btn btn-primary" @click="${this.handleTriggerWorldTick}">Advance World Tick</button>`
            : ''}
          <button class="btn ${this.isDrawerOpen ? 'btn-drawer active' : 'btn-secondary'}" @click="${this.toggleDrawer}">
            ${this.isDrawerOpen ? 'Hide Intel' : 'DM Intel Bulletin'}
          </button>
        </div>
      </div>
      <div class="radar-grid">
        ${this.renderRadarChart()}
        ${this.renderFactionCards()}
      </div>
      ${this.renderDmDrawer()}
      ${this.renderRumors()}
    `;
  }
}
