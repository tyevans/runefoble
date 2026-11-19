/**
 * Maps owner wire bodies to App Shell view models (TASK-0867, ADR-0015).
 *
 * Each mapper names the owner model it reads. Field names follow the owner model.
 * A required field that the owner does not send fails the read. No mapper fills
 * a required field with a default. `participantsCount` and the `campaign_id` /
 * `campaignId` reads belong to TASK-0771 and are kept as they were.
 */

import type { LobbyParticipant } from '@runefoble/game-session-ui';
import type { BoardToken, PartySeat } from '@runefoble/board-state-ui';
import type { CampaignSessionItem } from '../components/runefoble-session-list.ts';
import { dataOk, type DataResult } from './data-result.ts';
import {
  isBoolean, isInteger, isNonEmptyString, isPlainObject, isPositiveInteger, isString,
  malformedResponse, missingRequiredFields, requireFields, type RequiredFields,
} from './required-fields.ts';

/**
 * Required fields of a session as the App Shell maps it. Used for the session
 * list (CampaignSessionResponse, services/game_session/src/game_session/campaign/schemas.py:111)
 * and for one session (GameSessionState, services/game_session/src/game_session/models/session.py:22).
 */
export const SESSION_REQUIRED_FIELDS: RequiredFields = {
  id: isNonEmptyString,
  campaignId: isNonEmptyString,
  title: isString,
  status: isNonEmptyString,
  round: isPositiveInteger,
};

/**
 * Maps GameSessionState. The owner names the identifier `session_id` and the
 * round `combat_round`. It sends `participants` as a map keyed by player id.
 */
export function sessionFromOwner(data: any): DataResult<CampaignSessionItem> {
  return requireFields({
    id: data?.session_id,
    campaignId: data?.campaign_id || data?.campaignId,
    title: data?.title,
    status: data?.status,
    round: data?.combat_round,
    participantsCount: Array.isArray(data?.participants) ? data.participants.length : (data?.participantsCount || 0),
  }, SESSION_REQUIRED_FIELDS);
}

/** Fields the owner sends for each campaign member (CampaignMemberResponse, services/game_session/src/game_session/campaign/schemas.py:89). */
const MEMBER_FIELDS: RequiredFields = { user_id: isNonEmptyString, username: isNonEmptyString, role: isNonEmptyString };

/** Fields the owner sends for each participant (ParticipantState, services/game_session/src/game_session/models/session.py:13). */
const PARTICIPANT_FIELDS: RequiredFields = {
  player_id: isNonEmptyString,
  character_id: isNonEmptyString,
  character_name: isString,
  character_class: isString,
  is_present: isBoolean,
};

interface MemberLike { user_id: string; username?: string | null; role?: string | null }

/**
 * Builds the lobby roster from GameSessionState and the campaign member list.
 * The session owner sends no username or role, so they come from the member list.
 * A participant with no matching member fails the read.
 *
 * Readiness: the owner writes a `lobby_readiness` key only after a toggle
 * (lobby_transitions.with_readiness). A missing key means not ready.
 */
export function lobbyParticipantsFromOwner(state: any, members: MemberLike[]): DataResult<LobbyParticipant[]> {
  const participants = state?.participants;
  if (!isPlainObject(participants)) return malformedResponse('the session participants are not a map');
  const readiness = state?.lobby_readiness;
  if (!isPlainObject(readiness)) return malformedResponse('the session lobby_readiness is not a map');
  const out: LobbyParticipant[] = [];
  for (const entry of Object.values(participants)) {
    const missing = missingRequiredFields(entry, PARTICIPANT_FIELDS);
    if (missing.length > 0) return malformedResponse(`a participant is missing or invalid ${missing.join(', ')}`);
    const player = entry as Record<string, any>;
    const member = members.find((m) => m.user_id === player.player_id);
    if (!member) return malformedResponse(`no campaign member for participant ${player.player_id}`);
    const memberMissing = missingRequiredFields(member, MEMBER_FIELDS);
    if (memberMissing.length > 0) return malformedResponse(`campaign member ${member.user_id} is missing or invalid ${memberMissing.join(', ')}`);
    out.push({
      userId: player.player_id,
      username: member.username as string,
      role: member.role as string,
      isReady: readiness[player.player_id] === true,
      isAbsent: !player.is_present,
      characterId: player.character_id,
      characterName: player.character_name,
      characterClass: player.character_class,
    });
  }
  return dataOk(out);
}

/**
 * The seated characters of a GameSessionState, in seat order (TASK-0922). The battlemap set-up
 * places one token for each. A participant with a missing field fails the read.
 */
export function sessionSeatsFromOwner(state: any): DataResult<PartySeat[]> {
  const participants = state?.participants;
  if (!isPlainObject(participants)) return malformedResponse('the session participants are not a map');
  const seats: PartySeat[] = [];
  for (const entry of Object.values(participants)) {
    const missing = missingRequiredFields(entry, PARTICIPANT_FIELDS);
    if (missing.length > 0) return malformedResponse(`a participant is missing or invalid ${missing.join(', ')}`);
    const player = entry as Record<string, any>;
    seats.push({ characterId: player.character_id, characterName: player.character_name });
  }
  return dataOk(seats);
}

/** Required fields of a board (BoardState, services/board_state/src/board_state/models/board.py:18). */
const BOARD_REQUIRED_FIELDS: RequiredFields = { cols: isPositiveInteger, rows: isPositiveInteger };

/** Fields the owner sends for each token (PlacedTokenState, services/board_state/src/board_state/models/tokens.py:10). */
const TOKEN_FIELDS: RequiredFields = {
  token_id: isNonEmptyString,
  name: isString,
  x: isInteger,
  y: isInteger,
  vision_radius: isInteger,
};

/**
 * Maps BoardState. The owner sends `tokens` as a map keyed by token id.
 * `tokens` is optional: an absent map reads as an empty board.
 */
export function boardFromOwner(data: any): DataResult<{ cols: number; rows: number; tokens: BoardToken[] }> {
  const size = requireFields({ cols: data?.cols, rows: data?.rows }, BOARD_REQUIRED_FIELDS);
  if (!size.ok) return size;
  const tokens = data?.tokens ?? {};
  if (!isPlainObject(tokens)) return malformedResponse('the board tokens are not a map');
  const list: BoardToken[] = [];
  for (const entry of Object.values(tokens)) {
    const missing = missingRequiredFields(entry, TOKEN_FIELDS);
    if (missing.length > 0) return malformedResponse(`a board token is missing or invalid ${missing.join(', ')}`);
    const token = entry as Record<string, any>;
    list.push({
      id: token.token_id,
      name: token.name,
      x: token.x,
      y: token.y,
      hp: token.hp ?? undefined,
      visionRadius: token.vision_radius,
      activeAction: token.active_action ?? null,
    });
  }
  return dataOk({ cols: size.data.cols, rows: size.data.rows, tokens: list });
}
