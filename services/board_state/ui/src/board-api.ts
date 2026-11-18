/**
 * Public-route client for the tactical board microfrontend (TASK-0563).
 * Each function maps one UI event to one public HTTP route or WebSocket action.
 * Callers render the server response. They never show an optimistic result.
 */

import { postJson, wsUrl, type RequestOptions } from '@runefoble/ui-core';
import type { AoETemplateConfig } from './board-types.ts';

export interface TrapDraft {
  name: string;
  trapType: string;
  x: number;
  y: number;
  triggerType: 'step' | 'touch' | 'proximity';
  proximityRadius: number;
  dcDetection: number;
  damageDice: string;
  isSecret: boolean;
}

export interface SecretTrapResponse {
  trap_id: string;
  name?: string;
  is_armed?: boolean;
  [key: string]: unknown;
}

export interface SwitchMapDraft {
  newMapId: string;
  cols: number;
  rows: number;
  backgroundImageUrl: string;
  tokenTeleports: Record<string, [number, number]>;
}

export interface SwitchMapResponse {
  board_id: string;
  previous_map_id?: string | null;
  new_map_id: string;
  cols: number;
  rows: number;
  background_image_url?: string | null;
  teleported_tokens: Record<string, [number, number]>;
  status: string;
}

export function buildCreateTrapBody(draft: TrapDraft): Record<string, unknown> {
  return {
    name: draft.name,
    trap_type: draft.trapType,
    x: draft.x,
    y: draft.y,
    trigger_type: draft.triggerType,
    proximity_radius: draft.proximityRadius,
    dc_detection: draft.dcDetection,
    damage_dice: draft.damageDice,
    is_secret: draft.isSecret,
  };
}

/** POST /api/v1/boards/{boardId}/traps (DM only). */
export function postTrap(boardId: string, draft: TrapDraft, opts: RequestOptions = {}): Promise<SecretTrapResponse> {
  const url = `/api/v1/boards/${encodeURIComponent(boardId)}/traps`;
  return postJson<SecretTrapResponse>(url, buildCreateTrapBody(draft), opts);
}

/** POST /api/v1/boards/{boardId}/switch-map (DM only). */
export function postSwitchMap(boardId: string, draft: SwitchMapDraft, opts: RequestOptions = {}): Promise<SwitchMapResponse> {
  const url = `/api/v1/boards/${encodeURIComponent(boardId)}/switch-map`;
  return postJson<SwitchMapResponse>(url, {
    new_map_id: draft.newMapId,
    cols: draft.cols,
    rows: draft.rows,
    background_image_url: draft.backgroundImageUrl || null,
    token_teleports: draft.tokenTeleports,
  }, opts);
}

/** WebSocket URL of the board service stream, /ws/boards/{boardId}. */
export function boardSocketUrl(protocol: string, host: string, boardId: string): string {
  return wsUrl(`/ws/boards/${encodeURIComponent(boardId)}`, { protocol, host });
}

export interface TokenMoveIntent {
  tokenId: string;
  toX: number;
  toY: number;
}

/** Board socket action confirm_move, the contract read by the board service. */
export function buildConfirmMoveMessage(move: TokenMoveIntent): Record<string, unknown> {
  return {
    action: 'confirm_move',
    token_id: move.tokenId,
    to_x: move.toX,
    to_y: move.toY,
    initiated_by: 'player',
  };
}

/** Board socket action aoe_evaluate. The server replies with an aoe_preview broadcast. */
export function buildAoEEvaluateMessage(config: AoETemplateConfig): Record<string, unknown> {
  return {
    action: 'aoe_evaluate',
    shape: config.shape,
    origin_x: config.originX,
    origin_y: config.originY,
    direction_deg: config.directionDeg,
    radius_ft: config.radiusFt,
    length_ft: config.lengthFt,
    width_ft: config.widthFt,
    spell_name: config.spellName,
    caster_token_id: config.casterTokenId,
    grid_type: config.gridType ?? 'square',
  };
}
