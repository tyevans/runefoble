/**
 * App Shell data calls over the shared UI transport (TASK-0759).
 *
 * `requestData` sends one call through `request` from `@runefoble/ui-core` with the shell
 * bearer, and turns the outcome into a `DataResult`. Views keep the `DataResult` shape. The
 * error text comes from `HttpError`. Nothing returns substitute data.
 */

import { HttpError, request, UnreadableResponseError, type RequestSpec } from '@runefoble/ui-core';
import { shellAuth } from '../auth/transport.ts';
import { dataFailure, dataOk, NETWORK_FAILURE_MESSAGE, UNREADABLE_RESPONSE_MESSAGE, type DataFailure, type DataResult } from './data-result.ts';

/**
 * The `DataFailure` for an error of `request`. A refused call keeps its status and server
 * detail. A 2xx body that is not JSON is unreadable. A fetch `TypeError` is a network failure
 * with status 0. Any other error is a defect and is thrown again.
 */
export function dataFailureFromError(err: unknown): DataFailure {
  if (err instanceof HttpError) return dataFailure(err.status, err.detail);
  if (err instanceof UnreadableResponseError) return dataFailure(err.status, UNREADABLE_RESPONSE_MESSAGE);
  if (err instanceof TypeError) return dataFailure(0, NETWORK_FAILURE_MESSAGE);
  throw err;
}

/**
 * Sends `path` (on the page origin) with the shell bearer. An empty success body yields `{}`
 * cast to T. Callers that expect no body use `DataResult<void>`.
 */
export async function requestData<T>(path: string, spec: RequestSpec = {}, headers?: Record<string, string>): Promise<DataResult<T>> {
  try {
    const data = await request<T | undefined>(path, spec, { auth: shellAuth, headers });
    return dataOk((data ?? {}) as T);
  } catch (err) {
    return dataFailureFromError(err);
  }
}
