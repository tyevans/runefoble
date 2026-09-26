/**
 * Live WebRTC Voice Client & Room Signaling Adapter (TASK-0033, TASK-0068).
 *
 * Facade coordinating WebSocket signaling transport, PeerConnectionMesh,
 * and WebAudio pipeline integration.
 */

import { WebAudioPipeline } from './webaudio-pipeline.ts';
import { PeerConnectionMesh } from './webrtc-peer-mesh.ts';
import type { SignalingMessage, WebRTCVoiceOptions, WebRTCConnectionState } from './webrtc-types.ts';

export * from './webrtc-types.ts';
export * from './webrtc-peer-mesh.ts';

export class WebRTCVoiceService {
  private sessionId: string | null = null;
  private userId: string | null = null;
  private peerId: string | null = null;
  private role: string = 'player';
  private token?: string;
  private socket: WebSocket | null = null;
  private mesh: PeerConnectionMesh;
  private audioPipeline = new WebAudioPipeline();
  private telemetryInterval: number | null = null;
  private reconnectTimer: number | null = null;
  private connectionState: WebRTCConnectionState = 'disconnected';
  private options: WebRTCVoiceOptions;

  constructor(options: WebRTCVoiceOptions = {}) {
    const ws = typeof window !== 'undefined' && window.location
      ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
      : 'ws://localhost:8000';
    this.options = { wsBaseUrl: ws, iceServers: [{ urls: 'stun:stun.l.google.com:19302' }], autoReconnect: false, reconnectIntervalMs: 3000, ...options };
    this.mesh = new PeerConnectionMesh({ iceServers: this.options.iceServers, onSignal: (m) => this.sendSignalingMessage(m) });
  }

  public async connect(
    sessionId: string, userId: string, peerId?: string, role: string = 'player', token?: string
  ): Promise<void> {
    this.sessionId = sessionId;
    this.userId = userId;
    this.peerId = peerId || `peer_${userId}_${Math.random().toString(36).substring(2, 7)}`;
    this.role = role;
    this.token = token;
    this.setConnectionState('connecting');

    const q = new URLSearchParams({ session_id: sessionId, user_id: userId, peer_id: this.peerId, role: this.role });
    if (token) q.set('token', token);

    return new Promise((resolve, reject) => {
      try {
        this.socket = new WebSocket(`${this.options.wsBaseUrl}/ws/voice/${sessionId}?${q.toString()}`);
        this.socket.onopen = () => { this.setConnectionState('connected'); this.startTelemetryLoop(); resolve(); };
        this.socket.onmessage = async (e) => {
          try { await this.handleSignalingMessage(JSON.parse(e.data)); } catch (err) { this.options.onError?.(err as Error); }
        };
        this.socket.onerror = (err) => { this.setConnectionState('failed'); this.options.onError?.('Signaling error'); reject(err); };
        this.socket.onclose = (e) => {
          if (e.code === 4003) this.options.onError?.('Zanzibar permission denied: unable to connect to voice room');
          const prev = this.connectionState;
          this.cleanup();
          if (this.options.autoReconnect && prev === 'connected' && e.code !== 1000 && e.code !== 4003) this.scheduleReconnect();
        };
      } catch (err) { this.setConnectionState('failed'); reject(err); }
    });
  }

  public async startMicrophone(): Promise<MediaStream> {
    const stream = await this.audioPipeline.startMicrophone();
    for (const track of stream.getAudioTracks()) this.mesh.addLocalTrack(track, stream);
    return stream;
  }
  public applyDspFilters(filters: string[]): void { this.audioPipeline.applyDspFilters(filters); }
  public setMute(isMuted: boolean): void {
    this.audioPipeline.setMute(isMuted);
    this.sendSignalingMessage({ type: 'webrtc_mute', peer_id: this.peerId || '', is_muted: isMuted });
  }

  public getPeerId(): string | null { return this.peerId; }
  public getSessionId(): string | null { return this.sessionId; }
  public getUserId(): string | null { return this.userId; }
  public getConnectionState(): WebRTCConnectionState { return this.connectionState; }
  public getPeerMesh(): PeerConnectionMesh { return this.mesh; }
  public disconnect(): void {
    if (this.reconnectTimer !== null) { clearTimeout(this.reconnectTimer); this.reconnectTimer = null; }
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.sendSignalingMessage({ type: 'webrtc_leave', peer_id: this.peerId || '', reason: 'user_exit' });
      this.socket.close();
    }
    this.cleanup();
  }

  private cleanup(): void {
    if (this.telemetryInterval !== null) { clearInterval(this.telemetryInterval); this.telemetryInterval = null; }
    this.mesh.closeAll();
    this.audioPipeline.close();
    this.setConnectionState('disconnected');
  }

  private setConnectionState(state: WebRTCConnectionState): void {
    this.connectionState = state;
    this.options.onConnectionStateChange?.(state);
  }

  private scheduleReconnect(): void {
    this.setConnectionState('reconnecting');
    this.reconnectTimer = window.setTimeout(() => {
      if (this.sessionId && this.userId) this.connect(this.sessionId, this.userId, this.peerId || undefined, this.role, this.token).catch(() => {});
    }, this.options.reconnectIntervalMs || 3000);
  }

  private sendSignalingMessage(msg: SignalingMessage): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) this.socket.send(JSON.stringify(msg));
  }

  private async handleSignalingMessage(msg: SignalingMessage): Promise<void> {
    await this.mesh.handleSignal(msg, this.audioPipeline.getLocalStream(), this.peerId || '');
    if (msg.type === 'webrtc_joined' && msg.peers) {
      for (const p of msg.peers) {
        if (p.peer_id !== this.peerId) {
          this.options.onPeerJoined?.(p);
          await this.mesh.createPeerConnection(p.peer_id, true, this.audioPipeline.getLocalStream(), this.peerId || '');
        }
      }
    } else if (msg.type === 'webrtc_peer_joined' && msg.peer_id && msg.peer_id !== this.peerId) {
      this.options.onPeerJoined?.({ peer_id: msg.peer_id, user_id: msg.user_id || 'unknown', role: msg.role || 'player' });
    } else if (msg.type === 'webrtc_peer_muted' && msg.peer_id) {
      this.options.onPeerMuted?.(msg.peer_id, Boolean(msg.is_muted));
    } else if (msg.type === 'webrtc_peer_left' && msg.peer_id) {
      this.options.onPeerLeft?.(msg.peer_id, msg.reason);
    } else if (msg.type === 'webrtc_kicked') {
      this.options.onKicked?.(msg.reason || 'Kicked by DM');
      this.cleanup();
    }
  }

  private startTelemetryLoop(): void {
    if (this.telemetryInterval !== null) return;
    this.telemetryInterval = window.setInterval(() => {
      const { level, isSpeaking } = this.audioPipeline.getAudioLevel();
      this.options.onAudioLevel?.(level, isSpeaking);
      if (this.socket && this.socket.readyState === WebSocket.OPEN && this.peerId) {
        this.sendSignalingMessage({
          type: 'webrtc_telemetry', peer_id: this.peerId, audio_level: level, latency_ms: 15.0, is_speaking: isSpeaking,
        });
      }
    }, 250);
  }
}
