/**
 * Startup configuration for the SpiceDB preshared key (TASK-0625).
 *
 * The key is an operator secret. It has no default outside test mode.
 */

export const SPICEDB_PRESHARED_KEY_VAR = 'RUNEFOBLE_SPICEDB_PRESHARED_KEY';

/**
 * Read the SpiceDB preshared key from the environment.
 *
 * Throws at startup when the key is missing, unless NODE_ENV is "test". In test mode
 * the key may be empty, because tests do not reach a live SpiceDB.
 */
export function readSpicedbPresharedKey(env: NodeJS.ProcessEnv): string {
  const key = env[SPICEDB_PRESHARED_KEY_VAR];
  if (key) {
    return key;
  }
  if (env.NODE_ENV === 'test') {
    return '';
  }
  throw new Error(
    `${SPICEDB_PRESHARED_KEY_VAR} is not set. The SpiceDB preshared key is an operator secret and has no default.`
  );
}
