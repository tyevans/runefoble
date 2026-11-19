/**
 * Campaign Rules Tab (TASK-0878). Mounts the rules compendium inside a campaign.
 *
 * The campaign id reaches the compendium. The homebrew creator needs it to register a rule
 * for this campaign. The API base is the gateway origin, as on #/rules.
 */

import { html, type TemplateResult } from 'lit';

export function renderCampaignRulesTab(campaignId: string, canManage: boolean): TemplateResult {
  return html`<div class="rules-compendium-layout">
    <runefoble-rules-compendium
      .apiBaseUrl=${window.location.origin}
      .campaignId=${campaignId}
      .isDM=${canManage}
    ></runefoble-rules-compendium>
  </div>`;
}
