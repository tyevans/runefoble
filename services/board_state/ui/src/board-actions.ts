import type {
  AoETemplateConfig,
  BoardToken,
  RadialActionType,
  TerrainCell,
} from './board-types.ts';
import type { GhostPreviewEngine } from './ghost_preview.ts';
import { parseIncomingGhostPreview } from './ghost_preview.ts';
import { buildAoEEvaluateMessage } from './board-api.ts';
import { snapAngle } from './aoe_geometry.ts';

export interface BoardActionsHost {
  tokens: BoardToken[];
  /** The newest board version applied from a socket frame. Null before the first versioned frame. */
  boardVersion: number | null;
  activeAoE: AoETemplateConfig | null;
  aoeAffectedTokenIds: string[];
  aoeAffectedCells: [number, number][];
  ws: WebSocket | null;
  dispatchEvent(event: Event): boolean;
  requestUpdate(): void;
}

/**
 * Puts a new token list with a new token object on the host. The old list and token stay
 * as they were, so `changedProperties.has('tokens')` is true on the next update.
 */
export function replaceToken(
  host: { tokens: BoardToken[] },
  tokenId: string,
  patch: Partial<BoardToken>,
): BoardToken | undefined {
  let updated: BoardToken | undefined;
  host.tokens = host.tokens.map((t) => {
    if (t.id !== tokenId) return t;
    updated = { ...t, ...patch };
    return updated;
  });
  return updated;
}

/**
 * Maps the `token` of a server `token_placed` frame (PlacedTokenState) to a board token.
 * Returns null when the id, name or a whole-number cell is missing.
 */
export function boardTokenFromPlaced(token: any): BoardToken | null {
  if (typeof token?.token_id !== 'string' || !token.token_id || typeof token.name !== 'string') return null;
  if (!Number.isInteger(token.x) || !Number.isInteger(token.y)) return null;
  const mapped: BoardToken = { id: token.token_id, name: token.name, x: token.x, y: token.y };
  if (typeof token.hp === 'number') mapped.hp = token.hp;
  if (typeof token.vision_radius === 'number') mapped.visionRadius = token.vision_radius;
  if ('active_action' in token) mapped.activeAction = token.active_action ?? null;
  return mapped;
}

/**
 * Keeps the newest board version. Returns false for a frame that is older than the newest version
 * applied (TASK-0938). A snapshot read before a later move can arrive after that move's frame.
 * A frame without a version carries no order, so it is applied.
 */
function acceptBoardVersion(host: { boardVersion: number | null }, version: unknown): boolean {
  if (!Number.isInteger(version)) return true;
  const newest = version as number;
  if (host.boardVersion !== null && newest < host.boardVersion) return false;
  host.boardVersion = newest;
  return true;
}

/**
 * Applies the token snapshot of the board socket `connected` frame: a map of token id to
 * PlacedTokenState at subscribe time. The board can be read before its socket opens, so a move
 * saved in between is only in the snapshot. The server state replaces the shown token list,
 * unless the snapshot is older than a frame already applied. A frame without a token map
 * changes nothing.
 */
function applyConnectedSnapshot(host: { tokens: BoardToken[]; boardVersion: number | null }, frame: any): void {
  const tokens = frame.tokens;
  if (tokens === null || typeof tokens !== 'object' || Array.isArray(tokens)) return;
  if (!acceptBoardVersion(host, frame.version)) return;
  const shown = new Map(host.tokens.map((t) => [t.id, t]));
  const next: BoardToken[] = [];
  for (const entry of Object.values(tokens)) {
    const mapped = boardTokenFromPlaced(entry);
    if (mapped) next.push({ ...shown.get(mapped.id), ...mapped });
  }
  host.tokens = next;
}

/** Puts a placed token on a new list. A token with the same id is replaced. */
function addPlacedToken(host: { tokens: BoardToken[] }, token: BoardToken): void {
  const shown = host.tokens.some((t) => t.id === token.id);
  host.tokens = shown ? host.tokens.map((t) => (t.id === token.id ? token : t)) : [...host.tokens, token];
}

/**
 * Returns the text to show for a server `error` frame, or null for any other frame.
 * The board socket sends `{type: "error", code, message, action, token_id}` for a refused action.
 */
export function socketErrorMessage(data: any): string | null {
  if (data?.type !== 'error') return null;
  const message = typeof data.message === 'string' && data.message ? data.message : 'The board refused the action.';
  return typeof data.action === 'string' && data.action ? `${data.action} refused: ${message}` : message;
}

/** Ask the server to evaluate the active template. The result arrives as aoe_preview. */
export function requestAoEPreview(host: BoardActionsHost, config: AoETemplateConfig): void {
  if (host.ws && host.ws.readyState === WebSocket.OPEN) {
    host.ws.send(JSON.stringify(buildAoEEvaluateMessage(config)));
  }
}

export function executeRadialAction(
  host: BoardActionsHost,
  action: RadialActionType,
  tokenId: string
): void {
  const tok = replaceToken(host, tokenId, { activeAction: action });

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
      originX: tok ? tok.x : 2,
      originY: tok ? tok.y : 2,
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

  if (host.activeAoE) requestAoEPreview(host, host.activeAoE);
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
  if (action === 'ghost_preview' || action === 'preview_move' || action === 'runefoble.events.watcher.speech_intent_parsed') {
    const parsed = parseIncomingGhostPreview(data, host.tokens, host.terrainCells);
    if (parsed) host.ghostEngine?.stage(parsed);
  } else if (action === 'token_moved' || action === 'preview_cancelled') {
    host.ghostEngine?.cancel();
    if (action === 'token_moved') {
      if (typeof data.x === 'number' && typeof data.y === 'number' && acceptBoardVersion(host, data.version)) {
        replaceToken(host, data.token_id, { x: data.x, y: data.y });
      }
    }
  } else if (data.type === 'connected') {
    applyConnectedSnapshot(host, data);
  } else if (data.type === 'token_placed') {
    const placed = boardTokenFromPlaced(data.token);
    if (placed) addPlacedToken(host, placed);
  } else if (data.type === 'token_action_executed') {
    replaceToken(host, data.token_id, { activeAction: data.action });
  } else if (action === 'aoe_preview') {
    const active = host.activeAoE;
    const preview = data.template;
    const isCurrent =
      active !== null &&
      preview?.origin_x === active.originX &&
      preview?.origin_y === active.originY &&
      preview?.direction_deg === snapAngle(active.directionDeg) &&
      preview?.shape === active.shape;
    if (isCurrent) {
      host.aoeAffectedTokenIds = preview.affected_token_ids;
      host.aoeAffectedCells = preview.affected_cells;
      host.requestUpdate();
    }
  } else if (action === 'aoe_template_placed') {
    host.activeAoE = null;
    host.aoeAffectedTokenIds = [];
    host.aoeAffectedCells = [];
    host.requestUpdate();
  }
}
