import { html, nothing } from 'lit';
import type { BoardToken, TerrainCell } from '../board-types.ts';
import { getHealthBarColor } from './kinematics.template.ts';

export interface BoardCellProps {
  x: number;
  y: number;
  isRevealed: boolean;
  terrain?: TerrainCell;
  isWaypoint: boolean;
  isAoECell?: boolean;
  isTargeted?: boolean;
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
    isAoECell,
    isTargeted,
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
  const targeted = Boolean(isTargeted || token?.isTargeted);

  return html`
    <div
      class="cell ${!isRevealed ? 'fog' : ''} ${isDifficult ? 'difficult-terrain' : ''} ${hazardName ? 'hazard-cell' : ''} ${isWaypoint ? 'waypoint-path' : ''} ${isAoECell ? 'aoe-affected-cell' : ''}"
      @click="${() => isRevealed && onCellClick()}"
    >
      <span class="coord-label">${x},${y}</span>

      ${isDifficult ? html`<span class="terrain-badge difficult" title="Difficult terrain: +5ft">▲ +5ft</span>` : nothing}
      ${hazardName ? html`<span class="terrain-badge hazard" title="Hazard: ${hazardName}">⚠️ ${hazardName}</span>` : nothing}

      ${token && !isHiddenHostile
        ? html`
            <div class="token-container">
              <div
                class="token ${token.isAiControlled ? 'ai' : ''} ${token.isHostile ? 'hostile' : ''} ${isActiveTurn ? 'active-turn' : ''} ${targeted ? 'target-halo' : ''} ${draggingTokenId === token.id ? 'dragging' : ''}"
                style="background: ${token.color || 'var(--rf-accent-secondary)'}; ${selectedTokenId === token.id ? 'outline: 3px solid var(--rf-accent-primary);' : ''}"
                @pointerdown="${(e: PointerEvent) => onTokenPointerDown(e, token)}"
                title="${token.name}${token.isAiControlled ? ' (AI Stand-in)' : ''}${token.hp !== undefined ? ` [${token.hp}/${token.maxHp ?? token.hp} HP]` : ''}${isActiveTurn ? ' (Active Turn)' : ''}${targeted ? ' (Targeted by AoE)' : ''}"
              >
                ${token.name.slice(0, 2).toUpperCase()}
                ${token.activeAction ? html`<span class="token-action-badge">${token.activeAction}</span>` : nothing}
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
