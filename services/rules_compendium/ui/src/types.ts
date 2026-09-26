/**
 * TypeScript contracts and types for Rules Compendium microfrontends.
 * Governed by ADR-0004, ADR-0007, and ADR-0013.
 */

export type RuleCategory = 'all' | 'monster' | 'spell' | 'condition' | 'homebrew';

export type DifficultyTier = 'Easy' | 'Medium' | 'Hard' | 'Deadly';

export interface MonsterStatBlock {
  monster_id?: string;
  name: string;
  challenge_rating: number;
  creature_type: string;
  size?: string;
  armor_class: number;
  hit_points: number;
  speed?: string;
  xp: number;
  role: string;
  stats?: Record<string, number>;
  actions?: Array<{ name: string; desc: string }>;
  traits?: Array<{ name: string; desc: string }>;
  description?: string;
  is_homebrew?: boolean;
  campaign_id?: string | null;
}

export interface SpellModel {
  spell_id?: string;
  name: string;
  level: number;
  school: string;
  casting_time: string;
  range: string;
  components?: string;
  duration: string;
  description: string;
  is_homebrew?: boolean;
  campaign_id?: string | null;
}

export interface ConditionModel {
  condition_id?: string;
  name: string;
  description: string;
  effects: string[];
}

export interface RuleSearchResultItem {
  category: string;
  name: string;
  score: number;
  summary: string;
  details: Record<string, any>;
  is_homebrew?: boolean;
  campaign_id?: string | null;
}

export interface RuleSearchResponse {
  query: string;
  results_count: number;
  took_ms: number;
  results: RuleSearchResultItem[];
}

export interface MonsterGroupRecommendation {
  name: string;
  cr: number;
  xp: number;
  count: number;
  role: string;
  subtotal_xp: number;
}

export interface PartyXpThresholds {
  easy: number;
  medium: number;
  hard: number;
  deadly: number;
}

export interface EncounterBalanceRequest {
  party_levels: number[];
  target_difficulty: string;
  environment?: string | null;
  desired_roles?: string[] | null;
  campaign_id?: string | null;
}

export interface EncounterBalanceResponse {
  encounter_id: string;
  party_levels: number[];
  party_size: number;
  target_difficulty: string;
  difficulty_tier: string;
  total_party_xp_threshold: PartyXpThresholds;
  monsters: MonsterGroupRecommendation[];
  total_monster_count: number;
  total_raw_xp: number;
  multiplier: number;
  adjusted_xp: number;
  tactical_summary: string;
}

export interface HomebrewCreateRequest {
  campaign_id: string;
  rule_type: 'monster' | 'spell' | 'condition' | 'mechanic';
  title: string;
  content: Record<string, any>;
}

export interface HomebrewResponse {
  rule_id: string;
  campaign_id: string;
  author_id: string;
  rule_type: string;
  title: string;
  content: Record<string, any>;
  status: string;
}

export interface DraftMonsterEntry {
  name: string;
  cr: number;
  xp: number;
  role: string;
  count: number;
}
