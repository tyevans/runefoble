/**
 * Typed result for App Shell data calls (TASK-0640).
 *
 * Every read and write against the gateway returns a DataResult. A failed call
 * never returns canned data. Views render an error state or a toast instead.
 */

export type DataSuccess<T> = { ok: true; data: T };
export type DataFailure = { ok: false; status: number; message: string };
export type DataResult<T> = DataSuccess<T> | DataFailure;

export const NETWORK_FAILURE_MESSAGE = 'The gateway could not be reached. Check the connection and try again.';
export const UNREADABLE_RESPONSE_MESSAGE = 'The server sent a response that could not be read.';

export function dataOk<T>(data: T): DataSuccess<T> {
  return { ok: true, data };
}

export function dataFailure(status: number, message: string): DataFailure {
  return { ok: false, status, message };
}

/** Views use this to decide between the not-found and generic error states. */
export function isNotFound<T>(result: DataResult<T>): boolean {
  return !result.ok && result.status === 404;
}
