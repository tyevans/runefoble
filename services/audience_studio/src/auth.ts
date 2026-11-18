/**
 * SpiceDB Zanzibar client. Governed by ADR-0001 and libs/runefoble_auth/schema/runefoble.zed.
 *
 * The service holds no relationship state. It writes no tuples. Every permission check asks
 * SpiceDB. Without a live SpiceDB endpoint, every check is denied (TASK-0533 removed the local tuple store).
 */

export class ZanzibarClient {
  constructor(
    private readonly endpoint: string | undefined,
    private readonly token: string
  ) {}

  async checkPermission(
    resourceType: string,
    resourceId: string,
    permission: string,
    subjectType: string,
    subjectId: string
  ): Promise<boolean> {
    // Live SpiceDB check. No local fallback exists.
    if (this.endpoint?.startsWith('http')) {
      try {
        const resp = await fetch(`${this.endpoint}/v1/permissions/check`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${this.token}`,
          },
          body: JSON.stringify({
            resource: { objectType: resourceType, objectId: resourceId },
            permission,
            subject: { object: { objectType: subjectType, objectId: subjectId } },
          }),
        });
        if (resp.ok) {
          const body = (await resp.json()) as { permissionship?: string };
          return body.permissionship === 'PERMISSIONSHIP_HAS_PERMISSION';
        }
      } catch {
        // Unreachable SpiceDB denies the check.
      }
    }

    return false;
  }

  async isDungeonMaster(userId: string, campaignId: string): Promise<boolean> {
    return this.checkPermission(
      'campaign',
      campaignId,
      'run_session',
      'user',
      userId
    );
  }

  async isSpectatorOrViewer(
    userId: string,
    campaignId: string
  ): Promise<boolean> {
    return this.checkPermission(
      'campaign',
      campaignId,
      'view',
      'user',
      userId
    );
  }
}
