/**
 * Socket registry and fan-out for the audience WebSocket (TASK-0723).
 * Broadcasts go only to open sockets whose principal passes the schema check for the event.
 */

import { WebSocket } from 'ws';
import type { AudienceAccess } from '../access/audienceAccess.js';
import type { Logger } from '../logger.js';
import type { ClientContext, WSServerMessage } from '../types.js';

/** One event for one campaign. `render` builds the payload for a socket that may or may not approve. */
export interface CampaignEvent {
  type: WSServerMessage['type'];
  campaignId: string;
  pollId: string;
  requiresApprove: boolean;
  render: (canApprove: boolean) => unknown;
}

export class Broadcaster {
  private readonly sockets = new Map<WebSocket, ClientContext>();
  /** Broadcasts run one at a time, so every socket sees events in commit order. */
  private deliveries: Promise<void> = Promise.resolve();

  constructor(
    private readonly access: AudienceAccess,
    private readonly log: Logger
  ) {}

  register(socket: WebSocket, ctx: ClientContext): void {
    this.sockets.set(socket, ctx);
  }

  unregister(socket: WebSocket): void {
    this.sockets.delete(socket);
  }

  /** Queues one event behind the events before it. A failed delivery is logged and never stops the queue. */
  publish(event: CampaignEvent): void {
    this.deliveries = this.deliveries
      .then(() => this.deliver(event))
      .catch((err: unknown) => this.log.error({ err, type: event.type }, 'Audience broadcast failed'));
  }

  /** Sends one frame to one socket. A socket that is not open gets nothing. */
  send(socket: WebSocket, message: WSServerMessage): void {
    if (socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(message));
    }
  }

  private async deliver(event: CampaignEvent): Promise<void> {
    const targets = [...this.sockets.entries()].filter(
      ([sock, ctx]) => ctx.campaignId === event.campaignId && sock.readyState === WebSocket.OPEN
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
}
