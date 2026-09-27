export interface AmbushAlert {
  stage_index: number;
  ambush_type: string;
  danger_level: number;
  outcome: 'repelled' | 'cargo_damaged' | 'caravan_destroyed';
  cargo_loss_percentage: number;
  reported_by_campaign_id?: string;
  notes?: string;
}

export interface CaravanContractItem {
  contract_id: string;
  origin_outpost: string;
  destination_outpost: string;
  cargo: Record<string, number>;
  cargo_value: number;
  route_risk_level: 'low' | 'medium' | 'high' | 'deadly';
  transit_stages: number;
  current_stage?: number;
  escort_collateral: number;
  reward_gold: number;
  reward_reputation: number;
  posted_by_campaign_id?: string;
  contractor_campaign_id?: string;
  contractor_party_name?: string;
  status: 'open' | 'accepted' | 'in_transit' | 'fulfilled' | 'failed' | 'cancelled';
  expires_in_turns?: number;
  ambush_history?: AmbushAlert[];
  last_ambush?: AmbushAlert | null;
}
