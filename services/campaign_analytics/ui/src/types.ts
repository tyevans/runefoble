/**
 * Type definitions for Campaign Analytics & Chronicle Archive UI.
 * Governed by ADR-0004, ADR-0011, and ADR-0013.
 */

export interface HeatmapCell {
  x: number;
  y: number;
  density: number;
  movement_count: number;
  damage_total: number;
  hit_count: number;
  knockout_count: number;
}

export interface MovementCorridor {
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  count: number;
  tokenName?: string;
}

export interface HazardHotspot {
  x: number;
  y: number;
  hazardType: string;
  triggerCount: number;
}

export interface KnockoutLocation {
  x: number;
  y: number;
  characterName: string;
  round?: number;
}

export interface CampaignHeatmapResponse {
  campaign_id: string;
  session_id?: string | null;
  cell_size: number;
  metric: string;
  total_points: number;
  max_density: number;
  cells: HeatmapCell[];
  corridors?: MovementCorridor[];
  hazards?: HazardHotspot[];
  knockouts?: KnockoutLocation[];
}

export interface CombatantPerformance {
  combatant_id: string;
  combatant_name: string;
  damage_dealt: number;
  damage_taken: number;
  healing_provided: number;
  critical_hits: number;
  fumbles: number;
  turns_taken: number;
  mvp_score: number;
}

export interface MvpAward {
  title: string;
  recipient_id: string;
  recipient_name: string;
  metric_name: string;
  score: number;
  description: string;
}

export interface CampaignMvpResponse {
  campaign_id: string;
  session_id?: string | null;
  encounter_id?: string | null;
  overall_mvp?: MvpAward | null;
  awards: MvpAward[];
  combatants: CombatantPerformance[];
}

export interface TimelineMilestone {
  id: string;
  campaign_id: string;
  session_id: string;
  type: string;
  title: string;
  description: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface CampaignTimelineResponse {
  campaign_id: string;
  session_id?: string | null;
  total_milestones: number;
  milestones: TimelineMilestone[];
}
