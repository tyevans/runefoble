export interface WestMarchesDiscovery {
  discovery_id: string;
  name: string;
  discovery_type: string;
  coordinates: { x: number; y: number };
  discovered_by_campaign_id: string;
  discovered_by_party_name: string;
  description?: string;
  danger_level?: number;
  timestamp?: string;
  notes?: string;
  is_private?: boolean;
  metadata?: Record<string, any>;
}

export interface WestMarchesOutpost {
  outpost_id: string;
  name: string;
  region: string;
  level: number;
  facilities: Record<string, number>;
  contributing_campaigns: string[];
  stored_resources?: Record<string, number>;
  boons?: string[];
  defensive_buffer?: number;
}

export interface WestMarchesNotice {
  notice_id: string;
  campaign_id: string;
  author_name: string;
  party_name?: string;
  title: string;
  content: string;
  notice_type: string;
  bounty_reward?: number | string;
  posted_at?: string;
}

export const PARTY_COLORS: Record<string, string> = {
  'Party Blue': '#457b9d',
  'Party Gold': '#ffb703',
  'Nightstalkers': '#9b5de5',
  'Crimson Fangs': '#e63946',
};
