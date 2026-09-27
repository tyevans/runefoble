import type {
  AoETemplateConfig,
  BoardToken,
  RadialActionType,
  TerrainCell,
} from './board-types.ts';
import type { GhostPreviewEngine } from './ghost_preview.ts';
import { parseIncomingGhostPreview } from './ghost_preview.ts';

export interface BoardActionsHost {
  tokens: BoardToken[];
  activeAoE: AoETemplateConfig | null;
  aoeAffectedTokenIds: string[];
  aoeAffectedCells: [number, number][];
  ws: WebSocket | null;
  dispatchEvent(event: Event): boolean;
  requestUpdate(): void;
}

export function executeRadialAction(
  host: BoardActionsHost,
  action: RadialActionType,
  tokenId: string
): void {
  const tok = host.tokens.find((t) => t.id === tokenId);
  if (tok) tok.activeAction = action;

  host.dispatchEvent(
    new CustomEvent('token-action', {
      detail: { tokenId, action, tokenName: tok?.name },
      bubbles: true,
      composed: true,
    })
  );

  if (action === 'cast') {
    host.activeAoE = {
      shape: 'cone',
      originX: tok ? tok.x + 0.5 : 2.5,
      originY: tok ? tok.y + 0.5 : 2.5,
      directionDeg: 0,
      radiusFt: 15,
      spellName: 'Burning Hands',
      casterTokenId: tokenId,
    };
  }

  if (host.ws && host.ws.readyState === WebSocket.OPEN) {
    host.ws.send(
      JSON.stringify({
        action: 'token_action',
        token_id: tokenId,
        token_action: action,
      })
    );
  }

  host.requestUpdate();
}

export function confirmAoEPlacement(host: BoardActionsHost): void {
  if (!host.activeAoE) return;
  const template = host.activeAoE;
  const affectedTokens = host.aoeAffectedTokenIds;
  const affectedCells = host.aoeAffectedCells;

  host.dispatchEvent(
    new CustomEvent('aoe-place', {
      detail: { template, affectedTokenIds: affectedTokens, affectedCells },
      bubbles: true,
      composed: true,
    })
  );

  if (host.ws && host.ws.readyState === WebSocket.OPEN) {
    host.ws.send(
      JSON.stringify({
        action: 'aoe_place',
        shape: template.shape,
        origin_x: template.originX,
        origin_y: template.originY,
        direction_deg: template.directionDeg,
        radius_ft: template.radiusFt,
        length_ft: template.lengthFt,
        width_ft: template.widthFt,
        spell_name: template.spellName,
        caster_token_id: template.casterTokenId,
      })
    );
  }

  host.activeAoE = null;
  host.aoeAffectedTokenIds = [];
  host.aoeAffectedCells = [];
  host.requestUpdate();
}

export function cancelAoEPlacement(host: BoardActionsHost): void {
  host.dispatchEvent(new CustomEvent('aoe-cancel', { bubbles: true, composed: true }));
  host.activeAoE = null;
  host.aoeAffectedTokenIds = [];
  host.aoeAffectedCells = [];
  host.requestUpdate();
}

export function handleBoardSocketMessage(
  host: BoardActionsHost & {
    terrainCells: TerrainCell[];
    ghostEngine: GhostPreviewEngine | null;
  },
  data: any
): void {
  const action = data.action || data.type;
  if (action === 'ghost_preview' || action === 'preview_move' || action === 'SpeechIntentParsed') {
    const parsed = parseIncomingGhostPreview(data, host.tokens, host.terrainCells);
    if (parsed) host.ghostEngine?.stage(parsed);
  } else if (action === 'token_moved' || action === 'preview_cancelled') {
    host.ghostEngine?.cancel();
  } else if (action === 'token_action_executed') {
    const targetToken = host.tokens.find((t) => t.id === data.token_id);
    if (targetToken) {
      targetToken.activeAction = data.action;
      host.requestUpdate();
    }
  } else if (action === 'aoe_template_placed') {
    host.activeAoE = null;
    host.aoeAffectedTokenIds = [];
    host.aoeAffectedCells = [];
    host.requestUpdate();
  }
}
