/**
 * Required-field checks for App Shell mappers (TASK-0867, ADR-0015).
 *
 * A mapper lists its required fields in one constant. A missing or mistyped
 * required field makes the whole read fail. A mapper never fills it with a default.
 */

import { dataFailure, dataOk, type DataFailure, type DataResult } from './data-result.ts';

export type FieldCheck = (value: unknown) => boolean;

export type RequiredFields = Readonly<Record<string, FieldCheck>>;

export const isString: FieldCheck = (value) => typeof value === 'string';

export const isNonEmptyString: FieldCheck = (value) => typeof value === 'string' && value.length > 0;

export const isPositiveInteger: FieldCheck = (value) => Number.isInteger(value) && (value as number) >= 1;

export const isArray: FieldCheck = (value) => Array.isArray(value);

/** Returns the names of required fields that are absent or fail their check. */
export function missingRequiredFields(source: unknown, required: RequiredFields): string[] {
  const record = source !== null && typeof source === 'object' ? source as Record<string, unknown> : {};
  return Object.entries(required)
    .filter(([name, check]) => !check(record[name]))
    .map(([name]) => name);
}

/**
 * Returns the mapped item when every required field is present and valid.
 * Otherwise returns a failure that names the missing fields.
 */
export function requireFields<T extends object>(item: T, required: RequiredFields): DataResult<T> {
  const missing = missingRequiredFields(item, required);
  if (missing.length === 0) return dataOk(item);
  return malformedResponse(`missing or invalid ${missing.join(', ')}`);
}

/** Failure for a gateway body that breaks the mapper contract. HTTP 502: the upstream sent an invalid body. */
export function malformedResponse(reason: string): DataFailure {
  return dataFailure(502, `The server sent a response that is not valid: ${reason}.`);
}
