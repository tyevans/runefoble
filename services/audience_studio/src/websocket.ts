/**
 * Real-time WebSocket manager for live spectator polls and DM approval queue.
 * Governed by ADR-0001, ADR-0007, and ADR-0013.
 *
 * Every action runs as the handshake principal, and the engines check the schema permission
 * for that action (TASK-0554). Broadcasts go to sockets whose principal may see the event.
 * `proposal_queued` reaches only sockets with `audience_poll.approve`.
 *
 * Errors reach the client as typed `error` frames with fixed codes (TASK-0723). See ws/errorFrames.ts.
 */

import type { WebSocket } from 'ws';
import type { AudienceAccess } from './access/audienceAccess.js';
import { presentPoll, presentProposal } from './access/presentation.js';
import type { ApprovalQueue, ProposalAction } from './approvalQueue.js';
import type { Logger } from './logger.js';
import type { VerifiedPrincipal } from './identity/zitadelVerifier.js';
import type { PollEvent, PollEngine } from './pollEngine.js';
import type { ClientContext, WSServerMessage } from './types.js';
import { errorFrameFor } from './ws/errorFrames.js';
import { Broadcaster, type CampaignEvent } from './ws/broadcaster.js';
import { CommandDispatcher, parseClientMessage } from './ws/commandDispatcher.js';

const PROPOSAL_MESSAGE: Record<ProposalAction, WSServerMessage['type']> = {
  queued: 'proposal_queued',
  approved: 'proposal_approved',
  vetoed: 'proposal_vetoed',
};

export class WebSocketManager {
  private readonly broadcaster: Broadcaster;
  private readonly dispatcher: CommandDispatcher;

  constructor(
    pollEngine: PollEngine,
    approvalQueue: ApprovalQueue,
    access: AudienceAccess,
    private readonly log: Logger
  ) {
    this.broadcaster = new Broadcaster(access, log);
    this.dispatcher = new CommandDispatcher(pollEngine, approvalQueue);

    pollEngine.onPollEvent((event) => this.broadcaster.publish(pollEventToCampaignEvent(event)));

    approvalQueue.onProposalChange(({ action, proposal }) => {
      this.broadcaster.publish({
        type: PROPOSAL_MESSAGE[action],
        campaignId: proposal.campaignId,
        pollId: proposal.pollId,
        requiresApprove: action === 'queued',
        render: (canApprove) => presentProposal(proposal, canApprove),
      });
    });
  }

  /** Registers a socket that the handshake has already authorized for `campaignId`. */
  handleConnection(socket: WebSocket, campaignId: string, principal: VerifiedPrincipal): void {
    const ctx: ClientContext = { campaignId, principal };
    this.broadcaster.register(socket, ctx);

    this.broadcaster.send(socket, {
      type: 'connected',
      data: { campaignId, userId: principal.userId },
      message: 'Connected to audience stream channel',
    });

    socket.on('message', (raw: Buffer | string) => this.onMessage(socket, ctx, raw));

    socket.on('close', () => {
      this.broadcaster.unregister(socket);
    });
  }

  /** Handles one client frame. Every failure becomes an error frame. Only internal failures are logged here. */
  private async onMessage(socket: WebSocket, ctx: ClientContext, raw: Buffer | string): Promise<void> {
    let reply: WSServerMessage | undefined;
    try {
      reply = await this.dispatcher.dispatch(parseClientMessage(raw), ctx);
    } catch (err: unknown) {
      const frame = errorFrameFor(err);
      if (frame.code === 'internal_error') {
        this.log.error({ err, userId: ctx.principal.userId }, 'Audience WebSocket action failed');
      }
      this.broadcaster.send(socket, frame);
      return;
    }
    if (reply) this.broadcaster.send(socket, reply);
  }
}

function pollEventToCampaignEvent(event: PollEvent): CampaignEvent {
  const poll = event.poll;
  const base = { campaignId: poll.campaignId, pollId: poll.id, requiresApprove: false };
  if (event.type === 'vote_cast') {
    return {
      ...base,
      type: 'vote_cast',
      render: (canApprove) => ({ vote: event.vote, poll: presentPoll(poll, canApprove) }),
    };
  }
  return {
    ...base,
    type: event.type,
    render: (canApprove) => presentPoll(poll, canApprove),
  };
}
