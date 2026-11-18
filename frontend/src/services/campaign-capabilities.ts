/**
 * Campaign capability flags for the App Shell (TASK-0559).
 *
 * The gateway route `GET /api/v1/campaigns/{campaign_id}/capabilities` returns one boolean per
 * schema permission on `campaign` (runefoble.zed). The App Shell gates its views from these
 * flags and never reads a role string. The service checks stay authoritative. A flag only
 * controls what the client shows.
 */

export interface CampaignCapabilities {
  manage: boolean;
  run_session: boolean;
  play: boolean;
  view: boolean;
}
