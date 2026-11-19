/**
 * Role normalizer for the game session UI. TASK-0870.
 *
 * The UI reads role strings only through this module. Authorization stays on the server
 * (ADR-0001, Hard Invariant 1): owner and manage controls use the permission flags the
 * server returns, never these labels.
 */

export type NormalizedRole = 'owner' | 'dungeon_master' | 'player' | 'spectator' | 'unknown';

const ROLE_ALIASES: Readonly<Record<string, NormalizedRole>> = {
  owner: 'owner',
  dungeon_master: 'dungeon_master',
  dm: 'dungeon_master',
  player: 'player',
  spectator: 'spectator',
};

/** Roles that coordinate the session. They are not counted as players. */
const COORDINATOR_ROLES: ReadonlySet<NormalizedRole> = new Set<NormalizedRole>(['owner', 'dungeon_master']);

/** Display labels for each known role. */
export const ROLE_LABELS: Readonly<Record<Exclude<NormalizedRole, 'unknown'>, string>> = {
  owner: 'Owner',
  dungeon_master: 'Dungeon Master',
  player: 'Player',
  spectator: 'Spectator',
};

/** Maps a wire role string to a known role. Case and surrounding space are ignored. */
export function normalizeRole(role: string | null | undefined): NormalizedRole {
  const key = (role ?? '').trim().toLowerCase();
  return ROLE_ALIASES[key] ?? 'unknown';
}

/** True for owner and dungeon master roles. */
export function isCoordinatorRole(role: string | null | undefined): boolean {
  return COORDINATOR_ROLES.has(normalizeRole(role));
}

/** True for the spectator role. */
export function isSpectatorRole(role: string | null | undefined): boolean {
  return normalizeRole(role) === 'spectator';
}

/** True for the owner role. */
export function isOwnerRole(role: string | null | undefined): boolean {
  return normalizeRole(role) === 'owner';
}

/** True for the player role. */
export function isPlayerRole(role: string | null | undefined): boolean {
  return normalizeRole(role) === 'player';
}

/** True for the dungeon master role, under either wire name. */
export function isDungeonMasterRole(role: string | null | undefined): boolean {
  return normalizeRole(role) === 'dungeon_master';
}

/** Short badge labels for dense lists. */
export const ROLE_SHORT_LABELS: Readonly<Record<Exclude<NormalizedRole, 'unknown'>, string>> = {
  owner: 'Owner',
  dungeon_master: 'DM',
  player: 'Player',
  spectator: 'Spectator',
};
