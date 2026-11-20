/**
 * The absentee tactical stances (TASK-0954). The id is the value the stand-in guardrail policy
 * stores as `stance`. The server accepts only these three ids.
 */

export interface TacticalStance {
  id: string;
  name: string;
  icon: string;
  description: string;
}

export const TACTICAL_STANCES: TacticalStance[] = [
  { id: 'defensive', name: 'Defensive', icon: '🛡️', description: 'Protect allies & avoid melee' },
  { id: 'cautious', name: 'Cautious', icon: '⚖️', description: 'Conserve slots & ranged support' },
  { id: 'heroic', name: 'Heroic', icon: '⚔️', description: 'Bold smites & frontline focus' },
];
