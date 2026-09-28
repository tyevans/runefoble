import { html, type TemplateResult } from 'lit';
import type { FactionData } from './types.ts';

export interface FactionDetailsProps {
  factions: FactionData[];
  selectedFactionId?: string;
  onSelectFaction: (faction: FactionData) => void;
}

export function renderFactionCards(props: FactionDetailsProps): TemplateResult {
  const { factions, selectedFactionId, onSelectFaction } = props;
  if (factions.length === 0) {
    return html`<div class="empty-state">No factions available</div>`;
  }

  return html`
    <div class="factions-roster">
      ${factions.map((f) => {
        const isSelected = selectedFactionId === f.faction_id;
        const disp = f.disposition.toLowerCase();
        const goalPct = Math.min(100, Math.round((f.goal_progress / (f.goal_target || 100)) * 100));
        return html`
          <div class="faction-card ${isSelected ? 'selected' : ''}" @click="${() => onSelectFaction(f)}">
            <div class="faction-header">
              <span class="faction-name">${f.name}</span>
              <span class="disposition-badge disposition-${disp}">${f.disposition}</span>
            </div>
            <div class="faction-meta">
              ${f.territory ? html`<span class="chip-territory">📍 ${f.territory}</span>` : ''}
              ${f.rival_faction_ids?.length
                ? f.rival_faction_ids.map((r) => html`<span class="chip-territory">⚔️ ${r}</span>`)
                : ''}
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
