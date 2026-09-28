import { html, nothing } from 'lit';
import type { AoETemplateConfig, BoardToken } from '../board-types.ts';

export function renderBoardHeader(
  fogOfWar: boolean,
  onToggleFog: () => void,
  watcherStatus: string,
  enable3D?: boolean,
  onToggle3D?: () => void
) {
  return html`
    <div class="header">
      <div class="title"><span>⚔️ Tactical Realm</span></div>
      <div class="controls">
        <button class="fog-toggle ${fogOfWar ? 'active' : ''}" @click="${onToggleFog}" title="Toggle Fog of War visibility">
          🌫️ Fog of War: ${fogOfWar ? 'ON' : 'OFF'}
        </button>
        ${onToggle3D ? html`
          <button class="mode-3d-toggle ${enable3D ? 'active' : ''}" @click="${onToggle3D}" title="Toggle 3D Miniature Tabletop Physics">
            🎲 3D Mode: ${enable3D ? 'ON' : 'OFF'}
          </button>
        ` : nothing}
        <div class="watcher-badge">
          <span>👁️ The Watcher:</span>
          <span>${watcherStatus}</span>
        </div>
      </div>
    </div>
  `;
}

export function renderStatusBar(
  selectedTokenName: string | null,
  cols: number,
  rows: number
) {
  return html`
    <div class="status-bar">
      <span>Selected: ${selectedTokenName || 'None'}</span>
      <div class="legend">
        <span class="legend-item"><span class="dot" style="background: var(--rf-accent-tertiary)"></span> Turn</span>
        <span class="legend-item"><span class="dot" style="background: var(--rf-accent-primary)"></span> AI</span>
        <span class="legend-item"><span class="dot" style="background: var(--rf-accent-secondary)"></span> Player</span>
        <span class="legend-item"><span class="dot" style="background: repeating-linear-gradient(45deg, var(--rf-accent-tertiary), var(--rf-accent-tertiary) 2px, var(--rf-bg-surface) 2px, var(--rf-bg-surface) 4px)"></span> Difficult</span>
        <span class="legend-item"><span class="dot" style="background: var(--rf-accent-primary)"></span> Hazard</span>
      </div>
      <span>Grid: ${cols} x ${rows}</span>
    </div>
  `;
}

export function renderRadialMenuOverlay(
  radialToken: BoardToken | null,
  onSelect: (e: CustomEvent) => void,
  onClose: () => void
) {
  if (!radialToken) return nothing;
  return html`
    <runefoble-radial-menu
      style="position: absolute; left: ${(radialToken.x + 0.5) * 56}px; top: ${(radialToken.y + 0.5) * 56}px;"
      .tokenId=${radialToken.id}
      .tokenName=${radialToken.name}
      @action-select=${onSelect}
      @menu-close=${onClose}
    ></runefoble-radial-menu>
  `;
}

export function renderAoEOverlay(
  activeAoE: AoETemplateConfig | null,
  tokens: BoardToken[],
  cols: number,
  rows: number,
  onChange: (e: CustomEvent) => void
) {
  if (!activeAoE) return nothing;
  return html`
    <runefoble-aoe-template
      .shape=${activeAoE.shape}
      .originX=${activeAoE.originX}
      .originY=${activeAoE.originY}
      .directionDeg=${activeAoE.directionDeg}
      .radiusFt=${activeAoE.radiusFt ?? 15}
      .lengthFt=${activeAoE.lengthFt ?? 30}
      .widthFt=${activeAoE.widthFt ?? 5}
      .cellSizePx=${56}
      .spellName=${activeAoE.spellName ?? 'Spell Template'}
      .tokens=${tokens}
      .cols=${cols}
      .rows=${rows}
      @aoe-change=${onChange}
    ></runefoble-aoe-template>
  `;
}

export function renderAoEBanner(
  activeAoE: AoETemplateConfig | null,
  affectedCount: number,
  onConfirm: () => void,
  onCancel: () => void
) {
  if (!activeAoE) return nothing;
  return html`
    <div class="ghost-banner" style="border-left: 4px solid var(--rf-accent-primary, #e63946);">
      <div class="ghost-info">
        <span>✨ <strong>${activeAoE.spellName || 'Spell'}</strong>:</span>
        <span>${activeAoE.shape.toUpperCase()} (${activeAoE.radiusFt || activeAoE.lengthFt}ft, ${Math.round(activeAoE.directionDeg)}°)</span>
        <span>• ${affectedCount} Target(s) Enclosed</span>
      </div>
      <div class="ghost-actions">
        <button class="btn btn-confirm" @click="${onConfirm}" title="Cast spell affecting enclosed targets">✓ Confirm Cast</button>
        <button class="btn btn-cancel" @click="${onCancel}" title="Cancel template placement">✕ Cancel</button>
      </div>
    </div>
  `;
}
