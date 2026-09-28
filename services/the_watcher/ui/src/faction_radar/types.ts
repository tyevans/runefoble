export interface FactionShift {
  tick?: number;
  description: string;
  type?: string;
  timestamp?: string;
}

export interface FactionData {
  faction_id: string;
  campaign_id?: string;
  name: string;
  influence: number;
  resources: number;
  disposition: string;
  active_goal: string;
  goal_progress: number;
  goal_target: number;
  rival_faction_ids?: string[];
  territory?: string;
  shifts?: FactionShift[];
  history?: Array<Record<string, unknown>>;
}

export interface GeopoliticalShift {
  faction_id: string;
  faction_name: string;
  territory: string;
  shift_type: string;
  description: string;
  severity: string;
  ripple_effects: string[];
}

export interface WorldTickData {
  campaign_id: string;
  tick_number: number;
  intelligence_bulletin: string;
  factions?: FactionData[];
  shifts?: GeopoliticalShift[];
  tavern_rumors?: string[];
  timestamp: string;
}
