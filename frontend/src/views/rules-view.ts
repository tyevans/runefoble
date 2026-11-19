/**
 * Rules Compendium View. Mounts the vendored <runefoble-rules-compendium> at #/rules.
 *
 * The compendium owns its tabs: rules search, encounter builder, and homebrew. The encounter
 * builder is a tab of the compendium, so the view does not mount it a second time.
 *
 * The view passes the gateway origin. The compendium treats an empty API base as "not
 * configured" and does not search, so the view never passes an empty string. The route passes
 * no campaign id.
 */

import { html, type TemplateResult } from 'lit';
import type { RunefobleApp } from '../runefoble-app.ts';

export function renderRules(_app: RunefobleApp): TemplateResult {
  return html`<div class="rules-compendium-layout">
    <runefoble-rules-compendium
      .apiBaseUrl=${window.location.origin}
    ></runefoble-rules-compendium>
  </div>`;
}
