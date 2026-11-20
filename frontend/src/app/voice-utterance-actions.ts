/**
 * App Shell side of Push to Talk (TASK-0946).
 *
 * `<runefoble-voice-controls>` emits `voice-utterance` with a base64 WAV. It does not know the
 * session. The App Shell posts the audio to the gateway route `POST /api/v1/voice/transcribe` with
 * the signed-in user as the speaker, the session, and the speaker's board origin. voice_agent
 * transcribes it and forwards the transcript and the origin to The Watcher (TASK-0942).
 * The reply goes on `host.voiceUtterance`, which the session view binds to the element.
 * A failed upload is shown. No transcript is shown that the route did not return (ADR-0015).
 */

import type { RunefobleApp } from '../runefoble-app.ts';
import { speakerTokenCell } from './command-bar-context.ts';
import { requestData } from '../services/shell-request.ts';
import { isString, requireFields } from '../services/required-fields.ts';

/** The speaker's board token, its cell and the board size. The Watcher needs them for a move. */
export interface SpeakerBoardOrigin {
  token_id: string;
  from_x: number;
  from_y: number;
  grid_cols: number;
  grid_rows: number;
}

/** What `<runefoble-voice-controls>` shows for the last utterance. */
export interface VoiceUtteranceView {
  sending: boolean;
  transcript: string;
  watcherError: string;
  uploadError: string;
}

export const IDLE_VOICE_UTTERANCE: VoiceUtteranceView = { sending: false, transcript: '', watcherError: '', uploadError: '' };

const TRANSCRIBE_PATH = '/api/v1/voice/transcribe';

interface TranscribeReply {
  transcript: string;
  source: string;
  watcher_error?: string | null;
}

function failed(uploadError: string): VoiceUtteranceView {
  return { ...IDLE_VOICE_UTTERANCE, uploadError };
}

function failureText(status: number, message: string): string {
  return status > 0 ? `Push to Talk failed (${status}): ${message}` : `Push to Talk failed: ${message}`;
}

/**
 * The board origin of the character's token, as the board shows it (TASK-0945 `tokens-changed`).
 * Null without a board, or when the character has no token on it.
 */
export function speakerBoardOrigin(host: RunefobleApp, characterId: string | null | undefined): SpeakerBoardOrigin | null {
  const cell = speakerTokenCell(host.boardKind === 'board' ? host.shownTokens : [], characterId);
  if (cell.tokenId === null || cell.fromX === null || cell.fromY === null) return null;
  return { token_id: cell.tokenId, from_x: cell.fromX, from_y: cell.fromY, grid_cols: host.boardCols, grid_rows: host.boardRows };
}

/** The `voice-utterance` handler of the session view. The speaker's token is the character's token. */
export function handleVoiceUtterance(host: RunefobleApp, e: CustomEvent<{ audioBase64: string }>, characterId: string | null | undefined): Promise<void> {
  return sendVoiceUtterance(host, e.detail.audioBase64, speakerBoardOrigin(host, characterId));
}

/** Posts one utterance and puts the reply, or the failure, on `host.voiceUtterance`. */
export async function sendVoiceUtterance(host: RunefobleApp, audioBase64: string, origin: SpeakerBoardOrigin | null): Promise<void> {
  if (!host.sessionId || !host.campaignId || !host.currentUserId) {
    host.voiceUtterance = failed('Push to Talk failed: the session is not known.');
    return;
  }
  host.voiceUtterance = { ...IDLE_VOICE_UTTERANCE, sending: true };
  const body = {
    speaker_id: host.currentUserId,
    speaker_name: host.activeCharacter?.name || host.currentUserId,
    session_id: host.sessionId,
    campaign_id: host.campaignId,
    audio_base64: audioBase64,
    ...(origin ?? {}),
  };
  const sent = await requestData<TranscribeReply>(TRANSCRIBE_PATH, { method: 'POST', body: JSON.stringify(body) });
  const reply = sent.ok ? requireFields(sent.data, { transcript: isString }) : sent;
  if (!reply.ok) {
    host.voiceUtterance = failed(failureText(reply.status, reply.message));
    return;
  }
  if (!reply.data.transcript) {
    host.voiceUtterance = failed('No words were heard. Hold Push to Talk and speak again.');
    return;
  }
  host.voiceUtterance = {
    sending: false,
    transcript: reply.data.transcript,
    watcherError: reply.data.watcher_error ?? '',
    uploadError: '',
  };
}
