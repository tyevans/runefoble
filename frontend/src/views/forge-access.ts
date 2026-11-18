/**
 * Asset Forge access for the App Shell (TASK-0645, TASK-0644).
 *
 * The gateway returns `permissions` on each campaign. The App Shell reads the `manage` flag
 * to decide whether to show the Asset Forge tab and mount the forge elements. The forge
 * service checks its own permissions on each request. This check only shapes the view.
 */

export interface CampaignPermissionFlags {
  manage?: boolean;
}

export type ForgeAccess = 'allowed' | 'denied';

/** Returns `allowed` only when the campaign reports `permissions.manage`. A missing flag denies access. */
export function resolveForgeAccess(permissions: CampaignPermissionFlags | null | undefined): ForgeAccess {
  return permissions?.manage === true ? 'allowed' : 'denied';
}
