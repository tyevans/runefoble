import { html, nothing } from 'lit';
import type {
  BoardToken,
  DragKinematicsState,
  GhostPreviewState,
  TerrainCell,
} from './board-types.ts';
import { calculateVectorLineCoordinates } from './ghost_preview.ts';

export function getHealthBarColor(hp: number, maxHp: number): string {
  const ratio = Math.max(0, Math.min(1, hp / maxHp));
  if (ratio > 0.5) return 'var(--rf-accent-secondary)';
  if (ratio > 0.2) return 'var(--rf-accent-tertiary)';
  return 'var(--rf-accent-primary)';
}

export function renderVectorOverlay(
  ghostVector: ReturnType<typeof calculateVectorLineCoordinates> | null
) {
  if (!ghostVector) return nothing;
  return html`
    <svg class="vector-overlay" style="width: 100%; height: 100%;">
      <defs>
        <marker
          id="arrow"
          viewBox="0 0 10 10"
          refX="5"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--rf-accent-primary)" />
        </marker>
      </defs>
      <line
        class="vector-line"
        x1="${ghostVector.x1}"
        y1="${ghostVector.y1}"
        x2="${ghostVector.x2}"
        y2="${ghostVector.y2}"
        marker-end="url(#arrow)"
      />
    </svg>
  `;
}

export function renderDistanceRuler(dragState: DragKinematicsState | null) {
  if (!dragState?.isDragging || dragState.totalDistanceFt <= 0) return nothing;
  return html`
    <div class="distance-ruler">
      <span>📍 Distance: ${dragState.totalDistanceFt} ft</span>
      ${dragState.difficultCells.length > 0
        ? html`<span>(▲ +${dragState.difficultCells.length * 5}ft terrain)</span>`
        : nothing}
      ${dragState.hazardCells.length > 0
        ? html`<span>(⚠️ Hazard Alert)</span>`
        : nothing}
    </div>
  `;
}

export function renderGhostBanner(
  ghost: GhostPreviewState | null,
  onConfirm: () => void,
  onCancel: () => void
) {
  if (!ghost) return nothing;
  return html`
    <div class="ghost-banner">
      <div class="ghost-info">
        <span>👻 Spoken Preview:</span>
        <span>${ghost.tokenName || 'Character'} moves to (${ghost.toX}, ${ghost.toY})</span>
        <span>• ${ghost.totalDistanceFt} ft</span>
        ${ghost.hazardTriggered
          ? html`<span style="color: var(--rf-accent-primary)">⚠️ Triggers ${ghost.hazardTriggered} (${ghost.damageDice})</span>`
          : nothing}
        <span class="ghost-timer">⏱️ ${ghost.remainingSeconds}s</span>
      </div>
      <div class="ghost-actions">
        <button
          class="btn btn-confirm"
          @click="${onConfirm}"
          title="Confirm movement to destination"
        >
          ✓ Confirm Move
        </button>
        <button
          class="btn btn-cancel"
          @click="${onCancel}"
          title="Cancel preview"
        >
          ✕ Cancel
        </button>
      </div>
    </div>
  `;
}

export interface BoardCellProps {
  x: number;
  y: number;
  isRevealed: boolean;
  terrain?: TerrainCell;
  isWaypoint: boolean;
  token?: BoardToken;
  isActiveTurn: boolean;
  isGhostCell: boolean;
  ghostToken?: BoardToken | null;
  ghostName?: string;
  selectedTokenId: string | null;
  draggingTokenId?: string | null;
  onCellClick: () => void;
  onTokenPointerDown: (e: PointerEvent, token: BoardToken) => void;
  onGhostConfirm: () => void;
}

export function renderBoardCell(props: BoardCellProps) {
  const {
    x,
    y,
    isRevealed,
    terrain,
    isWaypoint,
    token,
    isActiveTurn,
    isGhostCell,
    ghostToken,
    ghostName,
    selectedTokenId,
    draggingTokenId,
    onCellClick,
    onTokenPointerDown,
    onGhostConfirm,
  } = props;

  const isDifficult = terrain?.terrainType === 'difficult';
  const hazardName = terrain?.hazard;
  const isHiddenHostile = token?.isHostile && !isRevealed;

  return html`
    <div
      class="cell ${!isRevealed ? 'fog' : ''} ${isDifficult ? 'difficult-terrain' : ''} ${hazardName ? 'hazard-cell' : ''} ${isWaypoint ? 'waypoint-path' : ''}"
      @click="${() => isRevealed && onCellClick()}"
    >
      <span class="coord-label">${x},${y}</span>

      ${isDifficult ? html`<span class="terrain-badge difficult" title="Difficult terrain: +5ft">▲ +5ft</span>` : nothing}
      ${hazardName ? html`<span class="terrain-badge hazard" title="Hazard: ${hazardName}">⚠️ ${hazardName}</span>` : nothing}

      ${token && !isHiddenHostile
        ? html`
            <div class="token-container">
              <div
                class="token ${token.isAiControlled ? 'ai' : ''} ${token.isHostile ? 'hostile' : ''} ${isActiveTurn ? 'active-turn' : ''} ${draggingTokenId === token.id ? 'dragging' : ''}"
                style="background: ${token.color || 'var(--rf-accent-secondary)'}; ${selectedTokenId === token.id ? 'outline: 3px solid var(--rf-accent-primary);' : ''}"
                @pointerdown="${(e: PointerEvent) => onTokenPointerDown(e, token)}"
                title="${token.name}${token.isAiControlled ? ' (AI Stand-in)' : ''}${token.hp !== undefined ? ` [${token.hp}/${token.maxHp ?? token.hp} HP]` : ''}${isActiveTurn ? ' (Active Turn)' : ''}"
              >
                ${token.name.slice(0, 2).toUpperCase()}
              </div>
              ${token.hp !== undefined && token.maxHp !== undefined
                ? html`
                    <div class="health-bar-container">
                      <div
                        class="health-bar-fill"
                        style="width: ${Math.max(0, Math.min(100, (token.hp / token.maxHp) * 100))}%; background: ${getHealthBarColor(token.hp, token.maxHp)};"
                      ></div>
                    </div>
                  `
                : nothing}
            </div>
          `
        : nothing}

      ${isGhostCell
        ? html`
            <div
              class="ghost-token"
              style="background: ${ghostToken?.color || 'var(--rf-accent-secondary)'};"
              @click="${onGhostConfirm}"
              title="Click to confirm move for ${ghostName || 'token'}"
            >
              ${(ghostName || ghostToken?.name || 'GH').slice(0, 2).toUpperCase()}
            </div>
          `
        : nothing}
    </div>
  `;
}

export function renderBoardHeader(
  fogOfWar: boolean,
  onToggleFog: () => void,
  watcherStatus: string
) {
  return html`
    <div class="header">
      <div class="title">
        <span>⚔️ Tactical Realm</span>
      </div>
      <div class="controls">
        <button
          class="fog-toggle ${fogOfWar ? 'active' : ''}"
          @click="${onToggleFog}"
          title="Toggle Fog of War visibility"
        >
          🌫️ Fog of War: ${fogOfWar ? 'ON' : 'OFF'}
        </button>
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
