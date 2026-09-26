/**
 * SpiceDB Zanzibar client and in-memory relationship store.
 * Governed by ADR-0001 and libs/runefoble_auth/schema/runefoble.zed.
 */

export interface RelationshipTuple {
  resourceType: string;
  resourceId: string;
  relation: string;
  subjectType: string;
  subjectId: string;
}

export class ZanzibarClient {
  private tuples: Set<string> = new Set();

  constructor(
    private readonly endpoint?: string,
    private readonly token?: string
  ) {}

  private tupleKey(
    resType: string,
    resId: string,
    rel: string,
    subType: string,
    subId: string
  ): string {
    return `${resType}:${resId}#${rel}@${subType}:${subId}`;
  }

  async writeRelationship(
    resourceType: string,
    resourceId: string,
    relation: string,
    subjectType: string,
    subjectId: string
  ): Promise<void> {
    const key = this.tupleKey(
      resourceType,
      resourceId,
      relation,
      subjectType,
      subjectId
    );
    this.tuples.add(key);

    // If live HTTP endpoint exists and is configured
    if (this.endpoint?.startsWith('http')) {
      try {
        await fetch(`${this.endpoint}/v1/relationships/write`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${this.token || 'runefoble_secret_key'}`,
          },
          body: JSON.stringify({
            updates: [
              {
                operation: 'OPERATION_TOUCH',
                relationship: {
                  resource: { objectType: resourceType, objectId: resourceId },
                  relation,
                  subject: {
                    object: { objectType: subjectType, objectId: subjectId },
                  },
                },
              },
            ],
          }),
        });
      } catch {
        // Fall back to in-memory store
      }
    }
  }

  async checkPermission(
    resourceType: string,
    resourceId: string,
    permission: string,
    subjectType: string,
    subjectId: string
  ): Promise<boolean> {
    // 1. Direct tuple match
    if (
      this.tuples.has(
        this.tupleKey(resourceType, resourceId, permission, subjectType, subjectId)
      )
    ) {
      return true;
    }

    // 2. Campaign hierarchy according to runefoble.zed
    if (resourceType === 'campaign') {
      const isOwner = this.tuples.has(
        this.tupleKey('campaign', resourceId, 'owner', subjectType, subjectId)
      );
      if (isOwner) return true;

      const isDM =
        this.tuples.has(
          this.tupleKey(
            'campaign',
            resourceId,
            'dungeon_master',
            subjectType,
            subjectId
          )
        ) ||
        this.tuples.has(
          this.tupleKey(
            'campaign',
            resourceId,
            'game_master',
            subjectType,
            subjectId
          )
        );

      if (isDM && ['run_session', 'dungeon_master', 'play', 'view'].includes(permission)) {
        return true;
      }

      const isPlayer = this.tuples.has(
        this.tupleKey('campaign', resourceId, 'player', subjectType, subjectId)
      );
      if (isPlayer && ['play', 'view'].includes(permission)) {
        return true;
      }

      const isSpectator = this.tuples.has(
        this.tupleKey('campaign', resourceId, 'spectator', subjectType, subjectId)
      );
      if (isSpectator && ['spectator', 'view'].includes(permission)) {
        return true;
      }
    }

    // 3. Live SpiceDB check if available
    if (this.endpoint?.startsWith('http')) {
      try {
        const resp = await fetch(`${this.endpoint}/v1/permissions/check`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${this.token || 'runefoble_secret_key'}`,
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
        // Fall back to in-memory check
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
