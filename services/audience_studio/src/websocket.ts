/**
 * Real-time WebSocket manager for live spectator polls and DM approval queue.
 * Governed by ADR-0001, ADR-0007, and ADR-0013.
 *
 * Every action runs as the handshake principal, and the engines check the schema permission
 * for that action (TASK-0554). Broadcasts go to sockets whose principal may see the event.
 * `proposal_queued` reaches only sockets with `audience_poll.approve`.
 */

import type { WebSocket } from 'ws';
import type { AudienceAccess } from './access/audienceAccess.js';
import { presentPoll, presentProposal } from './access/presentation.js';
import type { ApprovalQueue, ProposalAction } from './approvalQueue.js';
import type { Logger } from './logger.js';
import type { VerifiedPrincipal } from './identity/zitadelVerifier.js';
import type { PollEvent, PollEngine } from './pollEngine.js';
import type { WSClientMessage, WSServerMessage } from './types.js';

interface ClientContext {
  campaignId: string;
  /** Verified during the handshake. Every action acts as this principal. */
  principal: VerifiedPrincipal;
}

/** One event for one campaign. `render` builds the payload for a socket that may or may not approve. */
interface CampaignEvent {
  type: WSServerMessage['type'];
  campaignId: string;
  pollId: string;
  requiresApprove: boolean;
  render: (canApprove: boolean) => unknown;
}

const PROPOSAL_MESSAGE: Record<ProposalAction, WSServerMessage['type']> = {
  queued: 'proposal_queued',
  approved: 'proposal_approved',
  vetoed: 'proposal_vetoed',
};

export class WebSocketManager {
  private readonly sockets = new Map<WebSocket, ClientContext>();
  /** Broadcasts run one at a time, so every socket sees events in commit order. */
  private deliveries: Promise<void> = Promise.resolve();

  constructor(
    private readonly pollEngine: PollEngine,
    private readonly approvalQueue: ApprovalQueue,
    private readonly access: AudienceAccess,
    private readonly log: Logger
  ) {
    this.pollEngine.onPollEvent((event) => this.publish(this.pollEventToCampaignEvent(event)));

    this.approvalQueue.onProposalChange((action, proposal) => {
      this.publish({
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
    this.sockets.set(socket, { campaignId, principal });

    socket.send(
      JSON.stringify({
        type: 'connected',
        data: { campaignId, userId: principal.userId },
        message: 'Connected to audience stream channel',
      })
    );

    socket.on('message', async (raw: Buffer | string) => {
      try {
        const text = typeof raw === 'string' ? raw : raw.toString('utf-8');
        const msg = JSON.parse(text) as WSClientMessage;
        await this.handleMessage(socket, msg);
      } catch (err: unknown) {
        const errorMsg = err instanceof Error ? err.message : String(err);
        this.send(socket, { type: 'error', message: errorMsg });
      }
    });

    socket.on('close', () => {
      this.sockets.delete(socket);
    });
  }

  private async handleMessage(socket: WebSocket, msg: WSClientMessage): Promise<void> {
    const ctx = this.sockets.get(socket);
    if (!ctx) return;

    if (msg.action === 'ping') {
      this.send(socket, { type: 'pong' });
      return;
    }

    if (msg.action === 'subscribe') {
      this.send(socket, {
        type: 'subscribed',
        data: { campaignId: ctx.campaignId, userId: ctx.principal.userId },
      });
      return;
    }

    if (msg.action === 'cast_vote' && msg.pollId && msg.optionId) {
      await this.pollEngine.castVote(msg.pollId, ctx.principal, msg.optionId, msg.channel ?? 'ws');
      return;
    }

    if (msg.action === 'approve_proposal' && msg.proposalId) {
      const approved = await this.approvalQueue.approveProposal(msg.proposalId, ctx.principal);
      this.send(socket, { type: 'proposal_approved', data: approved });
      return;
    }

    if (msg.action === 'veto_proposal' && msg.proposalId) {
      const vetoed = await this.approvalQueue.vetoProposal(msg.proposalId, ctx.principal);
      this.send(socket, { type: 'proposal_vetoed', data: vetoed });
      return;
    }
  }

  private pollEventToCampaignEvent(event: PollEvent): CampaignEvent {
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

  private publish(event: CampaignEvent): void {
    this.deliveries = this.deliveries
      .then(() => this.deliver(event))
      .catch((err: unknown) => this.log.error({ err, type: event.type }, 'Audience broadcast failed'));
  }

  private async deliver(event: CampaignEvent): Promise<void> {
    const targets = [...this.sockets.entries()].filter(
      ([sock, ctx]) => ctx.campaignId === event.campaignId && sock.readyState === 1
    );
    for (const [socket, ctx] of targets) {
      try {
        const canApprove = await this.access.pollAllows(ctx.principal, event.pollId, 'approve');
        if (event.requiresApprove && !canApprove) continue;
        this.send(socket, { type: event.type, data: event.render(canApprove) });
      } catch (err: unknown) {
        // A failed check drops this one delivery. The failure is logged, and other sockets still receive the event.
        this.log.error({ err, type: event.type, userId: ctx.principal.userId }, 'Audience delivery check failed');
      }
    }
  }

  private send(socket: WebSocket, message: WSServerMessage): void {
    if (socket.readyState === 1) {
      socket.send(JSON.stringify(message));
    }
  }

  getClientCount(campaignId?: string): number {
    if (!campaignId) return this.sockets.size;
    let count = 0;
    for (const ctx of this.sockets.values()) {
      if (ctx.campaignId === campaignId) count++;
    }
    return count;
  }
}
