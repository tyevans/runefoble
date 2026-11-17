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

/** Pulls a human-readable message from a FastAPI-style error body, or falls back to the status code. */
export function errorMessageFromBody(body: unknown, status: number): string {
  if (body && typeof body === 'object') {
    const record = body as Record<string, unknown>;
    const detail = record.detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (Array.isArray(detail)) {
      const parts = detail
        .map((item) => (item && typeof item === 'object' && typeof (item as Record<string, unknown>).msg === 'string' ? String((item as Record<string, unknown>).msg) : ''))
        .filter(Boolean);
      if (parts.length > 0) return parts.join('; ');
    }
    if (typeof record.message === 'string' && record.message.trim()) return record.message;
    if (typeof record.error === 'string' && record.error.trim()) return record.error;
  }
  return status === 404 ? 'The requested item was not found.' : `The request failed with status ${status}.`;
}

/** Views use this to decide between the not-found and generic error states. */
export function isNotFound<T>(result: DataResult<T>): boolean {
  return !result.ok && result.status === 404;
}
