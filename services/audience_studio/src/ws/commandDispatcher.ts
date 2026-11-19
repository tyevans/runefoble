/**
 * Client command table for the audience WebSocket (TASK-0723). Each action maps to one handler.
 * Every handler acts as the handshake principal. The engines check the schema permission.
 */

import type { ApprovalQueue } from '../approvalQueue.js';
import type { PollEngine } from '../pollEngine.js';
import type { ClientContext, WSClientMessage, WSServerMessage } from '../types.js';
import { InvalidMessageError, UnknownActionError } from './errorFrames.js';

/** A handler returns the reply for its sender, or nothing when the result is a broadcast. */
type CommandHandler = (msg: WSClientMessage, ctx: ClientContext) => Promise<WSServerMessage | undefined>;

/** Parses one text frame into a client message. Throws InvalidMessageError for anything else. */
export function parseClientMessage(raw: Buffer | string): WSClientMessage {
  const text = typeof raw === 'string' ? raw : raw.toString('utf-8');
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new InvalidMessageError('Message is not valid JSON');
  }
  if (typeof parsed !== 'object' || parsed === null || typeof (parsed as { action?: unknown }).action !== 'string') {
    throw new InvalidMessageError('Message needs a string action');
  }
  return parsed as WSClientMessage;
}

function required(value: string | undefined, field: string): string {
  if (!value) throw new InvalidMessageError(`Field '${field}' is required`);
  return value;
}

export class CommandDispatcher {
  private readonly handlers: Map<string, CommandHandler>;

  constructor(pollEngine: PollEngine, approvalQueue: ApprovalQueue) {
    this.handlers = new Map<string, CommandHandler>([
      ['ping', async () => ({ type: 'pong' })],
      [
        'subscribe',
        async (_msg, ctx) => ({
          type: 'subscribed',
          data: { campaignId: ctx.campaignId, userId: ctx.principal.userId },
        }),
      ],
      [
        'cast_vote',
        async (msg, ctx) => {
          await pollEngine.castVote(
            required(msg.pollId, 'pollId'),
            ctx.principal,
            required(msg.optionId, 'optionId'),
            msg.channel ?? 'ws'
          );
          return undefined;
        },
      ],
      [
        'approve_proposal',
        async (msg, ctx) => {
          const approved = await approvalQueue.approveProposal(required(msg.proposalId, 'proposalId'), ctx.principal);
          return { type: 'proposal_approved', data: approved };
        },
      ],
      [
        'veto_proposal',
        async (msg, ctx) => {
          const vetoed = await approvalQueue.vetoProposal(required(msg.proposalId, 'proposalId'), ctx.principal);
          return { type: 'proposal_vetoed', data: vetoed };
        },
      ],
    ]);
  }

  /** Runs the handler for `msg.action`. Throws UnknownActionError when no handler exists. */
  dispatch(msg: WSClientMessage, ctx: ClientContext): Promise<WSServerMessage | undefined> {
    const handler = this.handlers.get(msg.action);
    if (!handler) return Promise.reject(new UnknownActionError(msg.action));
    return handler(msg, ctx);
  }
}
