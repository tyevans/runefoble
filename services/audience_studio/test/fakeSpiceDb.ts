/**
 * Fake SpiceDB at the authorization port (TASK-0554, orchestrator decision 3).
 *
 * SpiceDB is an external process, so the fake sits at that boundary. It is strict: an unknown
 * object type, relation, or permission throws, so a test cannot pass by accident. It knows only
 * the definitions that libs/runefoble_auth/schema/runefoble.zed gives `campaign` and `audience_poll`.
 * Tests grant campaign roles through `grant`. The service never calls it.
 */

import { DependencyUnavailableError } from '../src/errors.js';
import type { ObjectRef, PermissionQuery, RelationshipWrite, SpiceDbPort } from '../src/spicedb/spicedbPort.js';

/** `campaign` relations in runefoble.zed. */
const CAMPAIGN_RELATIONS = ['owner', 'dungeon_master', 'game_master', 'player', 'spectator'] as const;

/** `campaign` permissions, expanded to the relations that grant them. */
const CAMPAIGN_PERMISSIONS: Record<string, readonly string[]> = {
  run_session: ['owner', 'dungeon_master', 'game_master'],
  play: ['owner', 'dungeon_master', 'game_master', 'player'],
  view: ['owner', 'dungeon_master', 'game_master', 'player', 'spectator'],
};

/** `audience_poll` permissions, expressed as the campaign permission they reach through `campaign->`. */
const POLL_PERMISSIONS: Record<string, string> = {
  view: 'view',
  vote: 'view',
  moderate: 'run_session',
  approve: 'run_session',
  veto: 'run_session',
};

export class FakeSpiceDb implements SpiceDbPort {
  private readonly campaignRoles = new Set<string>();
  private readonly pollCampaign = new Map<string, string>();
  private unavailable = false;
  private writesUnavailable = false;
  /** Calls the service made, by kind. A listing must use `bulk` and never `single`. */
  readonly calls = { single: 0, bulk: 0 };

  /** Grants a campaign relation to a user, as a test would write it into SpiceDB. */
  grant(campaignId: string, relation: (typeof CAMPAIGN_RELATIONS)[number], userId: string): void {
    if (!(CAMPAIGN_RELATIONS as readonly string[]).includes(relation)) {
      throw new Error(`Relation '${relation}' is not defined on campaign`);
    }
    this.campaignRoles.add(roleKey(campaignId, relation, userId));
  }

  /** While set, every check fails the way an unreachable SpiceDB does. */
  setUnavailable(value: boolean): void {
    this.unavailable = value;
  }

  /** While set, every relationship write fails the way an unreachable SpiceDB does. Checks still answer. */
  setWritesUnavailable(value: boolean): void {
    this.writesUnavailable = value;
  }

  async checkPermission(query: PermissionQuery): Promise<boolean> {
    this.calls.single += 1;
    if (this.unavailable) {
      throw new DependencyUnavailableError('SpiceDB is unavailable (fake outage)');
    }
    return this.evaluate(query.resource, query.permission, query.subject);
  }

  async checkPermissions(queries: PermissionQuery[]): Promise<boolean[]> {
    this.calls.bulk += 1;
    if (this.unavailable) {
      throw new DependencyUnavailableError('SpiceDB is unavailable (fake outage)');
    }
    return queries.map((q) => this.evaluate(q.resource, q.permission, q.subject));
  }

  async writeRelationship(write: RelationshipWrite): Promise<void> {
    if (this.writesUnavailable) {
      throw new DependencyUnavailableError('SpiceDB is unavailable for writes (fake outage)');
    }
    const { resource, relation, subject } = write;
    if (subject.objectType !== 'campaign' && subject.objectType !== 'user') {
      throw new Error(`Subject type '${subject.objectType}' is not defined in the fake`);
    }
    if (resource.objectType === 'audience_poll' && relation === 'campaign' && subject.objectType === 'campaign') {
      this.pollCampaign.set(resource.objectId, subject.objectId);
      return;
    }
    if (resource.objectType === 'campaign' && subject.objectType === 'user') {
      this.grant(resource.objectId, relation as (typeof CAMPAIGN_RELATIONS)[number], subject.objectId);
      return;
    }
    throw new Error(`Relation '${relation}' on '${resource.objectType}' is not defined in the fake`);
  }

  private evaluate(resource: ObjectRef, permission: string, subject: ObjectRef): boolean {
    if (resource.objectType === 'campaign') {
      const relations = CAMPAIGN_PERMISSIONS[permission];
      if (!relations) throw new Error(`Permission '${permission}' is not defined on campaign`);
      return relations.some((rel) => this.campaignRoles.has(roleKey(resource.objectId, rel, subject.objectId)));
    }
    if (resource.objectType === 'audience_poll') {
      const campaignPermission = POLL_PERMISSIONS[permission];
      if (!campaignPermission) throw new Error(`Permission '${permission}' is not defined on audience_poll`);
      const campaignId = this.pollCampaign.get(resource.objectId);
      if (!campaignId) return false;
      return this.evaluate({ objectType: 'campaign', objectId: campaignId }, campaignPermission, subject);
    }
    throw new Error(`Object type '${resource.objectType}' is not defined in the fake`);
  }
}

function roleKey(campaignId: string, relation: string, userId: string): string {
  return `${campaignId}#${relation}@${userId}`;
}
