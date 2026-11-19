/**
 * OBS party vitals overlay data (TASK-0823 review).
 *
 * The App Shell route `#/overlay/party-vitals/:sessionId` mounts the vendored
 * `<runefoble-spectator-overlay>` for an OBS browser source. This module parses the route
 * query and reads the owner state from the gateway JSON route. It holds no state of its own.
 * The gateway route checks `session.observe` on every read.
 */

import { authHeaders } from '../auth/transport.ts';
import { dataFailure, dataOk, NETWORK_FAILURE_MESSAGE, UNREADABLE_RESPONSE_MESSAGE, type DataResult } from '../services/data-result.ts';

export const OVERLAY_POSITIONS = ['bottom', 'top', 'sidebar'] as const;
export type OverlayPosition = (typeof OVERLAY_POSITIONS)[number];

export const DEFAULT_OVERLAY_EASING = 'cubic-bezier(0.25, 0.1, 0.25, 1.0)';
export const DEFAULT_OVERLAY_DURATION_MS = 300;
const MAX_OVERLAY_DURATION_MS = 10000;
const BEZIER_PATTERN = /^cubic-bezier\(\s*-?[\d.]+\s*,\s*-?[\d.]+\s*,\s*-?[\d.]+\s*,\s*-?[\d.]+\s*\)$/;

export interface PartyVitalsOverlayOptions {
  position: OverlayPosition;
  easing: string;
  durationMs: number;
}

/**
 * Reads the overlay query values. A value that is missing or malformed takes its default.
 * These values only change how the overlay looks. They never change what the owner sends.
 */
export function parsePartyVitalsOverlayQuery(query: Record<string, string | undefined>): PartyVitalsOverlayOptions {
  const position = (OVERLAY_POSITIONS as readonly string[]).includes(query.position ?? '')
    ? (query.position as OverlayPosition)
    : 'bottom';
  const easing = query.easing && BEZIER_PATTERN.test(query.easing.trim()) ? query.easing.trim() : DEFAULT_OVERLAY_EASING;
  const duration = Number(query.duration);
  const durationMs = /^\d{1,5}$/.test(query.duration ?? '') && duration <= MAX_OVERLAY_DURATION_MS
    ? duration
    : DEFAULT_OVERLAY_DURATION_MS;
  return { position, easing, durationMs };
}

/** The gateway JSON for `GET /overlay/party-vitals/{session_id}`. Snake case, as the gateway sends it. */
export interface OwnerPartyMember {
  id: string;
  name: string;
  hp: number;
  max_hp: number;
}

export interface OwnerCameraTarget {
  target_x: number;
  target_y: number;
  zoom: number;
  duration_ms: number;
  easing: string;
  active_token_id?: string | null;
  reason?: string;
}

export interface PartyVitalsReply {
  session_id: string;
  party: OwnerPartyMember[];
  camera: OwnerCameraTarget;
  round: number;
  position: string;
  transparent: boolean;
}

/** The camelCase shape that `<runefoble-spectator-overlay>` takes as properties. */
export interface OverlayPartyMember {
  id: string;
  name: string;
  hp: number;
  maxHp: number;
}

export interface OverlayCamera {
  targetX: number;
  targetY: number;
  zoom: number;
  durationMs: number;
  easing: string;
  activeTokenId?: string;
  reason?: string;
}

export function toOverlayParty(party: OwnerPartyMember[]): OverlayPartyMember[] {
  return party.map((member) => ({ id: member.id, name: member.name, hp: member.hp, maxHp: member.max_hp }));
}

export function toOverlayCamera(camera: OwnerCameraTarget): OverlayCamera {
  return {
    targetX: camera.target_x,
    targetY: camera.target_y,
    zoom: camera.zoom,
    durationMs: camera.duration_ms,
    easing: camera.easing,
    activeTokenId: camera.active_token_id ?? undefined,
    reason: camera.reason,
  };
}

export type OverlayFetcher = (sessionId: string, position: OverlayPosition) => Promise<DataResult<PartyVitalsReply>>;

/** Reads the party vitals from the gateway with the viewer's bearer token. */
export const fetchPartyVitals: OverlayFetcher = async (sessionId, position) => {
  const url = `/overlay/party-vitals/${encodeURIComponent(sessionId)}?format=json&position=${position}`;
  let res: Response;
  try {
    res = await fetch(url, { headers: { Accept: 'application/json', ...authHeaders() } });
  } catch {
    return dataFailure(0, NETWORK_FAILURE_MESSAGE);
  }
  let body: unknown;
  try {
    body = await res.json();
  } catch {
    return dataFailure(res.status, UNREADABLE_RESPONSE_MESSAGE);
  }
  if (!res.ok) return dataFailure(res.status, `The overlay could not load (${res.status}).`);
  return dataOk(body as PartyVitalsReply);
};
