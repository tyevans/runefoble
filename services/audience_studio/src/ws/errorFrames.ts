/**
 * Maps any failure on the audience WebSocket to a typed `error` frame (TASK-0723).
 *
 * Only errors that the HTTP routes already show to clients keep their text. Every other failure
 * gets a fixed message. The real error is logged by the caller, never sent to the socket.
 */

import { Forbidden, HttpError } from '../errors.js';
import type { WSErrorCode } from '../types.js';

/** The frame was not valid JSON, or a known action lacks a required field. */
export class InvalidMessageError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'InvalidMessageError';
  }
}

/** The `action` value is not in the command table. */
export class UnknownActionError extends Error {
  constructor(action: string) {
    super(`Unknown action '${action}'`);
    this.name = 'UnknownActionError';
  }
}

export interface ErrorFrame {
  type: 'error';
  code: WSErrorCode;
  message: string;
}

const INTERNAL_MESSAGE = 'The server could not complete the request.';

/** Returns the frame to send for `err`. The caller logs the error when `code` is `internal_error`. */
export function errorFrameFor(err: unknown): ErrorFrame {
  if (err instanceof InvalidMessageError) {
    return { type: 'error', code: 'invalid_message', message: err.message };
  }
  if (err instanceof UnknownActionError) {
    return { type: 'error', code: 'unknown_action', message: err.message };
  }
  if (err instanceof Forbidden) {
    return { type: 'error', code: 'forbidden', message: err.message };
  }
  if (err instanceof HttpError && err.statusCode < 500) {
    return { type: 'error', code: 'rejected', message: err.message };
  }
  return { type: 'error', code: 'internal_error', message: INTERNAL_MESSAGE };
}
