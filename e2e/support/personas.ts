/**
 * Test personas for the Playwright BDD suite (TASK-0525, ADR-0014).
 *
 * Global setup creates each persona as a real Zitadel human user through the management API.
 * Each run uses unique login names, so runs do not collide. The registry travels to the worker
 * processes in one environment variable. It is never written to disk.
 */

export const PERSONA_KEYS = ['dm', 'player', 'evelyn', 'valeros', 'sarah', 'marcus'] as const;
export type PersonaKey = (typeof PERSONA_KEYS)[number];

export interface PersonaSeed {
  key: PersonaKey;
  givenName: string;
  familyName: string;
}

export const PERSONA_SEEDS: Record<PersonaKey, PersonaSeed> = {
  dm: { key: 'dm', givenName: 'Dungeon Master', familyName: 'Eldrin' },
  player: { key: 'player', givenName: 'Player', familyName: 'Adventurer' },
  evelyn: { key: 'evelyn', givenName: 'Evelyn', familyName: 'Vance' },
  valeros: { key: 'valeros', givenName: 'Valeros', familyName: 'of Korvosa' },
  sarah: { key: 'sarah', givenName: 'Sarah', familyName: 'Shadowstep' },
  marcus: { key: 'marcus', givenName: 'Marcus', familyName: 'Ironhand' },
};

/** A persona that exists in Zitadel for this run. Carries the password, so it stays in memory only. */
export interface PersonaRecord {
  key: PersonaKey;
  userId: string;
  loginName: string;
  password: string;
}

export const PERSONA_REGISTRY_ENV = 'RUNEFOBLE_E2E_PERSONAS';

/**
 * Maps a step phrase ("DM", "Dungeon Master", "Valeros") to a persona key.
 * An unknown name is an error. The suite never falls back to another persona.
 */
export function resolvePersonaKey(roleOrName: string): PersonaKey {
  const normalized = roleOrName.toLowerCase().replace(/[^a-z]/g, '');
  const named = PERSONA_KEYS.find((key) => key !== 'dm' && key !== 'player' && normalized.includes(key));
  if (named) return named;
  if (['dm', 'master', 'gm', 'dungeonmaster'].some((alias) => normalized.includes(alias))) return 'dm';
  if (normalized.includes('player')) return 'player';
  throw new Error(`Unknown test persona "${roleOrName}". Add it to PERSONA_KEYS.`);
}

export function readPersonaRegistry(): PersonaRecord[] {
  const raw = process.env[PERSONA_REGISTRY_ENV];
  if (!raw) {
    throw new Error('Test personas are missing. Run the suite through make test-e2e so global setup creates them.');
  }
  return JSON.parse(raw) as PersonaRecord[];
}

export function findPersona(key: PersonaKey): PersonaRecord {
  const persona = readPersonaRegistry().find((record) => record.key === key);
  if (!persona) throw new Error(`Persona "${key}" was not created by global setup.`);
  return persona;
}
