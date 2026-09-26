/**
 * Real-time WebSocket manager for live spectator polls and DM approval queue.
 * Governed by ADR-0001, ADR-0007, and ADR-0013.
 */

import type { WebSocket } from 'ws';
import type { ApprovalQueue } from './approvalQueue.js';
import type { PollEngine } from './pollEngine.js';
import type { WSClientMessage, WSServerMessage } from './types.js';

interface ClientContext {
  campaignId: string;
  userId?: string;
  role?: string;
}

export class WebSocketManager {
  private sockets: Map<WebSocket, ClientContext> = new Map();

  constructor(
    private readonly pollEngine: PollEngine,
    private readonly approvalQueue: ApprovalQueue
  ) {
    // Listen to poll events and broadcast
    this.pollEngine.onPollEvent((event, data) => {
      const campaignId = (data as { campaignId?: string; poll?: { campaignId?: string } })
        ?.campaignId || (data as { poll?: { campaignId?: string } })?.poll?.campaignId;
      if (campaignId) {
        this.broadcast(campaignId, { type: event, data });
      }
    });

    // Listen to approval queue events and broadcast
    this.approvalQueue.onProposalChange((action, proposal) => {
      const type =
        action === 'queued'
          ? 'proposal_queued'
          : action === 'approved'
          ? 'proposal_approved'
          : 'proposal_vetoed';
      this.broadcast(proposal.campaignId, { type, data: proposal });
    });
  }

  handleConnection(socket: WebSocket, campaignId: string): void {
    this.sockets.set(socket, { campaignId });

    socket.send(
      JSON.stringify({
        type: 'connected',
        data: { campaignId },
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

  private async handleMessage(
    socket: WebSocket,
    msg: WSClientMessage
  ): Promise<void> {
    const ctx = this.sockets.get(socket);
    if (!ctx) return;

    if (msg.action === 'ping') {
      this.send(socket, { type: 'pong' });
      return;
    }

    if (msg.action === 'subscribe') {
      if (msg.userId) ctx.userId = msg.userId;
      if (msg.role) ctx.role = msg.role;
      this.send(socket, {
        type: 'subscribed',
        data: { campaignId: ctx.campaignId, userId: ctx.userId, role: ctx.role },
      });
      return;
    }

    if (msg.action === 'cast_vote' && msg.pollId && msg.optionId && msg.userId) {
      await this.pollEngine.castVote(
        msg.pollId,
        msg.userId,
        msg.optionId,
        msg.channel ?? 'ws'
      );
      return;
    }

    if (msg.action === 'approve_proposal' && msg.proposalId && msg.userId) {
      const approved = await this.approvalQueue.approveProposal(
        msg.proposalId,
        msg.userId
      );
      this.send(socket, { type: 'proposal_approved', data: approved });
      return;
    }

    if (msg.action === 'veto_proposal' && msg.proposalId && msg.userId) {
      const vetoed = await this.approvalQueue.vetoProposal(
        msg.proposalId,
        msg.userId
      );
      this.send(socket, { type: 'proposal_vetoed', data: vetoed });
      return;
    }
  }

  broadcast(campaignId: string, message: WSServerMessage): void {
    const payload = JSON.stringify(message);
    for (const [sock, ctx] of this.sockets.entries()) {
      if (ctx.campaignId === campaignId && sock.readyState === 1) {
        try {
          sock.send(payload);
        } catch {
          // Ignore socket write errors
        }
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
