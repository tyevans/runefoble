/**
 * Object-level authorization for Audience Studio. Governed by ADR-0001 and Hard Invariant 1.
 *
 * The service checks permissions only through SpiceDB. Role names never appear in this file.
 * Permission names are the ones in libs/runefoble_auth/schema/runefoble.zed:
 * - `campaign`: `view` (play + spectator) and `run_session` (owner + dungeon_master + game_master).
 * - `audience_poll`: `view` and `vote` (campaign view), `moderate`, `approve`, and `veto`
 *   (campaign run_session). A poll links to its campaign through the `campaign` relation.
 */

import { Unauthenticated, Forbidden } from '../errors.js';
import type { VerifiedPrincipal } from '../identity/zitadelVerifier.js';
import type { ObjectRef, SpiceDbPort } from '../spicedb/spicedbPort.js';

export type CampaignPermission = 'view' | 'run_session';
export type PollPermission = 'view' | 'vote' | 'moderate' | 'approve' | 'veto';

function subjectOf(actor: VerifiedPrincipal | undefined): ObjectRef {
  if (!actor) {
    throw new Unauthenticated('A verified principal is required');
  }
  return { objectType: 'user', objectId: actor.userId };
}

export class AudienceAccess {
  constructor(private readonly spicedb: SpiceDbPort) {}

  campaignAllows(actor: VerifiedPrincipal | undefined, campaignId: string, permission: CampaignPermission): Promise<boolean> {
    return this.spicedb.checkPermission({
      resource: { objectType: 'campaign', objectId: campaignId },
      permission,
      subject: subjectOf(actor),
    });
  }

  pollAllows(actor: VerifiedPrincipal | undefined, pollId: string, permission: PollPermission): Promise<boolean> {
    return this.spicedb.checkPermission({
      resource: { objectType: 'audience_poll', objectId: pollId },
      permission,
      subject: subjectOf(actor),
    });
  }

  async requireCampaign(actor: VerifiedPrincipal | undefined, campaignId: string, permission: CampaignPermission): Promise<void> {
    if (!(await this.campaignAllows(actor, campaignId, permission))) {
      throw new Forbidden(`Permission '${permission}' is required on the campaign`);
    }
  }

  async requirePoll(actor: VerifiedPrincipal | undefined, pollId: string, permission: PollPermission): Promise<void> {
    if (!(await this.pollAllows(actor, pollId, permission))) {
      throw new Forbidden(`Permission '${permission}' is required on the audience poll`);
    }
  }

  /** Writes the `campaign` relation that lets campaign permissions reach the poll. */
  async bindPollToCampaign(pollId: string, campaignId: string): Promise<void> {
    await this.spicedb.writeRelationship({
      resource: { objectType: 'audience_poll', objectId: pollId },
      relation: 'campaign',
      subject: { objectType: 'campaign', objectId: campaignId },
    });
  }
}
