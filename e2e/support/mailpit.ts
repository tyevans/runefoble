/**
 * Reads account mail from Mailpit in the local render (ADR-0023 b, TASK-0950).
 *
 * The test reads the mail that Zitadel sends. It never writes Zitadel state. Mailpit is
 * development only. A hosted render has no `/mail` route.
 */

import type { APIRequestContext } from '@playwright/test';
import { API_BASE_URL } from './env';

const MAILPIT_API = `${API_BASE_URL}/mail/api/v1`;
const POLL_INTERVAL_MS = 1_000;

interface MailpitListReply {
  messages: Array<{ ID: string; To: Array<{ Address: string }> }>;
}

interface MailpitMessageReply {
  Text: string;
}

/** Waits for the newest message to `address` and returns its plain text. */
export async function waitForMailText(request: APIRequestContext, address: string, timeoutMs = 60_000): Promise<string> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const list = await request.get(`${MAILPIT_API}/messages?limit=50`);
    if (!list.ok()) {
      throw new Error(`Mailpit did not list messages: ${list.status()} ${list.statusText()}`);
    }
    const listed = (await list.json()) as MailpitListReply;
    const wanted = address.toLowerCase();
    const match = listed.messages.find((item) => item.To.some((to) => to.Address.toLowerCase() === wanted));
    if (match) {
      const message = await request.get(`${MAILPIT_API}/message/${match.ID}`);
      if (!message.ok()) {
        throw new Error(`Mailpit did not return message ${match.ID}: ${message.status()}`);
      }
      return ((await message.json()) as MailpitMessageReply).Text;
    }
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
  }
  throw new Error(`No Mailpit message for ${address} within ${timeoutMs} ms.`);
}

/** The Zitadel link in the mail text. It opens the hosted page where the person sets a password. */
export function extractZitadelLink(text: string): string {
  const links = text.match(/https?:\/\/[^\s"<>]+/g) ?? [];
  const link = links.find((candidate) => candidate.includes('/ui/login/'));
  if (!link) {
    throw new Error('The account mail has no Zitadel link.');
  }
  return link;
}
