/**
 * App Shell Session Socket (TASK-0640b).
 *
 * Owns the live session WebSocket for the App Shell. It opens the socket on session and
 * lobby routes, closes it on other routes, reconnects after a drop, and applies incoming
 * messages to the host. A session_started message for the shell's own session, with status
 * `active`, navigates through the router to the shell's own route (TASK-0910). A session_ended
 * message for the shell's own session shows the recap (TASK-0953).
 */

import { wsUrl } from '@runefoble/ui-core';
import { authService } from '../auth/auth-service.ts';
import { wsProtocols } from '../auth/transport.ts';
import { router, type MatchedRoute } from '../router/index.ts';
import type { RunefobleApp } from '../runefoble-app.ts';
import { applySessionEndedFrame, handleSessionMessage, sessionStartedRoute } from './session-messages.ts';

const RECONNECT_DELAY_MS = 4000;
/** Close code the gateway sends when it refuses the WebSocket handshake (ADR-0015 c). */
export const HANDSHAKE_REFUSED_CODE = 1008;

/** Builds the session WebSocket URL on the current origin. Call only in a browser. */
export function sessionSocketUrl(sessionId: string): string {
  return wsUrl(`/ws/session/${sessionId}`);
}

export class SessionSocket {
  private socket: WebSocket | null = null;
  private activeSessionId: string | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  private readonly host: RunefobleApp;

  constructor(host: RunefobleApp) {
    this.host = host;
  }

  /** The open socket, or null when no session route is active. */
  get current(): WebSocket | null {
    return this.socket;
  }

  /** Opens the socket on session and lobby routes and closes it on every other route. */
  manageWebSocketLifecycle(route: MatchedRoute): void {
    if (route.pattern.includes('/sessions/') || route.pattern.includes('/lobby/')) {
      const target = route.params.sessionId || this.host.sessionId;
      if (!this.socket || this.activeSessionId !== target) this.connectWebSocket(target);
    } else {
      this.disconnectWebSocket();
    }
  }

  connectWebSocket(sessionId: string): void {
    this.disconnectWebSocket();
    this.activeSessionId = sessionId;
    try {
      if (typeof window === 'undefined' || typeof WebSocket === 'undefined') return;
      const protocols = wsProtocols();
      if (!protocols) {
        this.host.showToast('Sign in to open the live session.');
        return;
      }
      this.socket = new WebSocket(sessionSocketUrl(sessionId), protocols);
      this.socket.onopen = () => {
        this.host.socketConnected = true;
      };
      this.socket.onmessage = (e) => this.handleMessage(e.data);
      this.socket.onclose = (event) => {
        this.host.socketConnected = false;
        if (event.code === HANDSHAKE_REFUSED_CODE) {
          this.refuseSession();
          return;
        }
        const pattern = router.getCurrentRoute()?.pattern || '';
        if (pattern.includes('/sessions/') || pattern.includes('/lobby/')) {
          this.reconnectTimer = setTimeout(() => this.connectWebSocket(this.host.sessionId), RECONNECT_DELAY_MS);
        }
      };
    } catch (error) {
      console.error('Session socket failed to open.', error);
      this.host.socketConnected = false;
      this.host.showToast('The live session connection failed. Reload the page to retry.');
    }
  }

  /** The gateway refused the handshake. Clear the session and send the user to sign-in. */
  private refuseSession(): void {
    this.socket = null;
    this.activeSessionId = null;
    authService.discardSession();
    this.host.showToast('Your sign-in was not accepted. Sign in again.');
  }

  disconnectWebSocket(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.socket) {
      this.socket.onclose = null;
      this.socket.close();
      this.socket = null;
    }
    this.activeSessionId = null;
    this.host.socketConnected = false;
  }

  private handleMessage(data: string): void {
    try {
      const msg = JSON.parse(data);
      if (msg.type === 'session_started') {
        const route = sessionStartedRoute(this.host, msg);
        if (route) router.navigate(route);
      } else if (msg.type === 'session_ended') {
        applySessionEndedFrame(this.host, msg);
      } else {
        handleSessionMessage(this.host, msg);
      }
    } catch (error) {
      console.error('Session message failed.', error);
      this.host.showToast('A live session message could not be applied. The board may be out of date.');
    }
  }
}
