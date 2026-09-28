import { html, type TemplateResult } from 'lit';
import type { WorldTickData } from './types.ts';

export interface BulletinDrawerProps {
  isOpen: boolean;
  isDm: boolean;
  bulletin: WorldTickData | null;
  onClose: () => void;
}

export function renderDmDrawer(props: BulletinDrawerProps): TemplateResult | null {
  const { isOpen, isDm, bulletin, onClose } = props;
  if (!isOpen) return null;
  if (!isDm) {
    return html`
      <div class="redacted-box">
        🔒 Classified: SpiceDB Zanzibar Redaction Active.<br />
        Private DM intelligence briefings and background tactical moves are hidden from players.
      </div>
    `;
  }

  const shifts = bulletin?.shifts || [];
  const bulletinText = bulletin?.intelligence_bulletin || '';

  return html`
    <div class="dm-drawer">
      <div class="drawer-header">
        <div class="drawer-title"><span>👁️ The Watcher Secret DM Briefing</span></div>
        <button class="btn" @click="${onClose}">Close</button>
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

export function renderRumors(rumors: string[]): TemplateResult {
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
