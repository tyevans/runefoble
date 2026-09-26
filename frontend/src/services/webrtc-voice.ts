/**
 * Live WebRTC Voice Client & Room Signaling Adapter (TASK-0033).
 *
 * Manages RTCPeerConnection mesh connections, WebAudio pipeline integration,
 * and real-time WebSocket signaling.
 */

import { WebAudioPipeline } from './webaudio-pipeline.ts';

export interface VoicePeer {
  peer_id: string;
  user_id: string;
  role: string;
  joined_at?: string;
  is_muted?: boolean;
  audio_level?: number;
  latency_ms?: number;
  is_speaking?: boolean;
}

export interface SignalingMessage {
  type: string;
  session_id?: string;
  peer_id?: string;
  from_peer?: string;
  to_peer?: string;
  user_id?: string;
  role?: string;
  sdp?: RTCSessionDescriptionInit;
  candidate?: RTCIceCandidateInit;
  is_muted?: boolean;
  audio_level?: number;
  latency_ms?: number;
  is_speaking?: boolean;
  reason?: string;
  peers?: VoicePeer[];
}

export interface WebRTCVoiceOptions {
  wsBaseUrl?: string;
  iceServers?: RTCIceServer[];
  onPeerJoined?: (peer: VoicePeer) => void;
  onPeerLeft?: (peerId: string, reason?: string) => void;
  onPeerMuted?: (peerId: string, isMuted: boolean) => void;
  onAudioLevel?: (level: number, isSpeaking: boolean) => void;
  onKicked?: (reason: string) => void;
  onError?: (error: Error | string) => void;
}

export class WebRTCVoiceService {
  private sessionId: string | null = null;
  private userId: string | null = null;
  private peerId: string | null = null;
  private role: string = 'player';

  private socket: WebSocket | null = null;
  private peerConnections = new Map<string, RTCPeerConnection>();
  private remoteStreams = new Map<string, MediaStream>();

  private audioPipeline: WebAudioPipeline = new WebAudioPipeline();
  private telemetryInterval: number | null = null;
  private options: WebRTCVoiceOptions;

  constructor(options: WebRTCVoiceOptions = {}) {
    this.options = {
      wsBaseUrl:
        typeof window !== 'undefined' && window.location
          ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
          : 'ws://localhost:8000',
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' },
      ],
      ...options,
    };
  }

  public async connect(
    sessionId: string,
    userId: string,
    peerId?: string,
    role: string = 'player',
    token?: string
  ): Promise<void> {
    this.sessionId = sessionId;
    this.userId = userId;
    this.peerId = peerId || `peer_${userId}_${Math.random().toString(36).substring(2, 7)}`;
    this.role = role;

    const query = new URLSearchParams({
      session_id: sessionId,
      user_id: userId,
      peer_id: this.peerId,
      role: this.role,
    });
    if (token) query.set('token', token);

    const wsUrl = `${this.options.wsBaseUrl}/ws/voice/${sessionId}?${query.toString()}`;

    return new Promise((resolve, reject) => {
      try {
        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
          this.startTelemetryLoop();
          resolve();
        };

        this.socket.onmessage = async (event) => {
          try {
            const data: SignalingMessage = JSON.parse(event.data);
            await this.handleSignalingMessage(data);
          } catch (err) {
            this.options.onError?.(err as Error);
          }
        };

        this.socket.onerror = (err) => {
          this.options.onError?.('WebSocket voice signaling error');
          reject(err);
        };

        this.socket.onclose = (event) => {
          if (event.code === 4003) {
            this.options.onError?.('Zanzibar permission denied: unable to connect to voice room');
          }
          this.cleanup();
        };
      } catch (e) {
        reject(e);
      }
    });
  }

  public async startMicrophone(): Promise<MediaStream> {
    const stream = await this.audioPipeline.startMicrophone();
    for (const pc of this.peerConnections.values()) {
      for (const track of stream.getAudioTracks()) {
        pc.addTrack(track, stream);
      }
    }
    return stream;
  }

  public applyDspFilters(filters: string[]): void {
    this.audioPipeline.applyDspFilters(filters);
  }

  public setMute(isMuted: boolean): void {
    this.audioPipeline.setMute(isMuted);
    this.sendSignalingMessage({
      type: 'webrtc_mute',
      peer_id: this.peerId || '',
      is_muted: isMuted,
    });
  }

  public getPeerId(): string | null {
    return this.peerId;
  }

  public getSessionId(): string | null {
    return this.sessionId;
  }

  public getUserId(): string | null {
    return this.userId;
  }


  public disconnect(): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.sendSignalingMessage({
        type: 'webrtc_leave',
        peer_id: this.peerId || '',
        reason: 'user_exit',
      });
      this.socket.close();
    }
    this.cleanup();
  }

  private cleanup(): void {
    if (this.telemetryInterval !== null) {
      clearInterval(this.telemetryInterval);
      this.telemetryInterval = null;
    }
    for (const pc of this.peerConnections.values()) {
      pc.close();
    }
    this.peerConnections.clear();
    this.remoteStreams.clear();
    this.audioPipeline.close();
  }

  private sendSignalingMessage(message: SignalingMessage): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    }
  }

  private async handleSignalingMessage(msg: SignalingMessage): Promise<void> {
    switch (msg.type) {
      case 'webrtc_joined':
        if (msg.peers) {
          for (const peer of msg.peers) {
            if (peer.peer_id !== this.peerId) {
              this.options.onPeerJoined?.(peer);
              await this.createPeerConnection(peer.peer_id, true);
            }
          }
        }
        break;

      case 'webrtc_peer_joined':
        if (msg.peer_id && msg.peer_id !== this.peerId) {
          this.options.onPeerJoined?.({
            peer_id: msg.peer_id,
            user_id: msg.user_id || 'unknown',
            role: msg.role || 'player',
          });
        }
        break;

      case 'webrtc_offer':
        if (msg.from_peer && msg.sdp) {
          const pc = await this.createPeerConnection(msg.from_peer, false);
          await pc.setRemoteDescription(new RTCSessionDescription(msg.sdp));
          const answer = await pc.createAnswer();
          await pc.setLocalDescription(answer);
          this.sendSignalingMessage({
            type: 'webrtc_answer',
            from_peer: this.peerId || '',
            to_peer: msg.from_peer,
            sdp: answer,
          });
        }
        break;

      case 'webrtc_answer':
        if (msg.from_peer && msg.sdp) {
          const pc = this.peerConnections.get(msg.from_peer);
          if (pc) {
            await pc.setRemoteDescription(new RTCSessionDescription(msg.sdp));
          }
        }
        break;

      case 'webrtc_ice_candidate':
        if (msg.from_peer && msg.candidate) {
          const pc = this.peerConnections.get(msg.from_peer);
          if (pc) {
            await pc.addIceCandidate(new RTCIceCandidate(msg.candidate));
          }
        }
        break;

      case 'webrtc_peer_muted':
        if (msg.peer_id) {
          this.options.onPeerMuted?.(msg.peer_id, Boolean(msg.is_muted));
        }
        break;

      case 'webrtc_peer_left':
        if (msg.peer_id) {
          const pc = this.peerConnections.get(msg.peer_id);
          if (pc) {
            pc.close();
            this.peerConnections.delete(msg.peer_id);
          }
          this.remoteStreams.delete(msg.peer_id);
          this.options.onPeerLeft?.(msg.peer_id, msg.reason);
        }
        break;

      case 'webrtc_kicked':
        this.options.onKicked?.(msg.reason || 'Kicked by DM');
        this.cleanup();
        break;
    }
  }

  private async createPeerConnection(remotePeerId: string, isInitiator: boolean): Promise<RTCPeerConnection> {
    if (this.peerConnections.has(remotePeerId)) {
      return this.peerConnections.get(remotePeerId)!;
    }

    const pc = new RTCPeerConnection({ iceServers: this.options.iceServers });
    this.peerConnections.set(remotePeerId, pc);

    pc.onicecandidate = (event) => {
      if (event.candidate) {
        this.sendSignalingMessage({
          type: 'webrtc_ice_candidate',
          from_peer: this.peerId || '',
          to_peer: remotePeerId,
          candidate: event.candidate.toJSON(),
        });
      }
    };

    pc.ontrack = (event) => {
      if (event.streams && event.streams[0]) {
        this.remoteStreams.set(remotePeerId, event.streams[0]);
      }
    };

    const localStream = this.audioPipeline.getLocalStream();
    if (localStream) {
      for (const track of localStream.getAudioTracks()) {
        pc.addTrack(track, localStream);
      }
    }

    if (isInitiator) {
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      this.sendSignalingMessage({
        type: 'webrtc_offer',
        from_peer: this.peerId || '',
        to_peer: remotePeerId,
        sdp: offer,
      });
    }

    return pc;
  }

  private startTelemetryLoop(): void {
    if (this.telemetryInterval !== null) return;

    this.telemetryInterval = window.setInterval(() => {
      const { level, isSpeaking } = this.audioPipeline.getAudioLevel();

      this.options.onAudioLevel?.(level, isSpeaking);

      if (this.socket && this.socket.readyState === WebSocket.OPEN && this.peerId) {
        this.sendSignalingMessage({
          type: 'webrtc_telemetry',
          peer_id: this.peerId,
          audio_level: level,
          latency_ms: 15.0,
          is_speaking: isSpeaking,
        });
      }
    }, 250);
  }
}
