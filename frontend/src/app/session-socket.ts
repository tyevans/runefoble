/**
 * App Shell Session Socket (TASK-0640b).
 *
 * Owns the live session WebSocket for the App Shell. It opens the socket on session and
 * lobby routes, closes it on other routes, reconnects after a drop, and applies incoming
 * messages to the host. A session_started message navigates through the router.
 */

import { authService } from '../auth/auth-service.ts';
import { router, type MatchedRoute } from '../router/index.ts';
import type { RunefobleApp } from '../runefoble-app.ts';
import { handleSessionMessage } from './session-messages.ts';

const RECONNECT_DELAY_MS = 4000;

/** Builds the session WebSocket URL on the current origin. Call only in a browser. */
export function sessionSocketUrl(sessionId: string): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host || 'localhost:8000'}/ws/session/${sessionId}`;
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
      const token = authService.getAccessToken();
      if (!token) return;
      this.socket = new WebSocket(sessionSocketUrl(sessionId), ['runefoble.v1', `runefoble.bearer.${token}`]);
      this.socket.onopen = () => {
        this.host.socketConnected = true;
      };
      this.socket.onmessage = (e) => this.handleMessage(e.data);
      this.socket.onclose = () => {
        this.host.socketConnected = false;
        const pattern = router.getCurrentRoute()?.pattern || '';
        if (pattern.includes('/sessions/') || pattern.includes('/lobby/')) {
          this.reconnectTimer = setTimeout(() => this.connectWebSocket(this.host.sessionId), RECONNECT_DELAY_MS);
        }
      };
    } catch {
      this.host.socketConnected = false;
    }
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
        router.navigate(`#/campaigns/${msg.campaignId || this.host.campaignId}/sessions/${msg.sessionId || this.host.sessionId}`);
      } else {
        handleSessionMessage(this.host, msg);
      }
    } catch { /* ignore */ }
  }
}
