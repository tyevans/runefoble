export interface AtlasPin {
  pin_id: string;
  title: string;
  layer: string;
  coordinates: { x: number; y: number };
  description?: string;
  era?: string;
  session_id?: string;
  linked_entity_ids?: string[];
  metadata?: Record<string, any>;
}

export interface AtlasTerritory {
  territory_id: string;
  name: string;
  layer: string;
  polygon_coordinates: number[][];
  owner_faction: string;
  is_contested: boolean;
  era?: string;
  metadata?: Record<string, any>;
}

export interface CodexEntry {
  entry_id: string;
  title: string;
  content: string;
  illuminated_content?: string;
  privacy: 'private' | 'party_shared' | 'public';
  author_id: string;
  era?: string;
  tags?: string[];
  linked_entities?: Array<{ id: string; name: string; entity_type: string }>;
}
