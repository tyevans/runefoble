/**
 * Asset Forge access for the App Shell (TASK-0645, TASK-0644, TASK-0559).
 *
 * The App Shell reads the `manage` capability to decide whether to show the Asset Forge tab
 * and mount the forge elements. The forge service checks its own permissions on each request.
 * This check only shapes the view.
 */

import type { CampaignCapabilities } from '../services/campaign-capabilities.ts';

export type ForgeAccess = 'allowed' | 'denied';

/** Returns `allowed` only when the caller holds the `manage` capability. A missing flag denies access. */
export function resolveForgeAccess(capabilities: Partial<Pick<CampaignCapabilities, 'manage'>> | null | undefined): ForgeAccess {
  return capabilities?.manage === true ? 'allowed' : 'denied';
}
