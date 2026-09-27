/**
 * WebRTC Protocol Types & Connection Interfaces (TASK-0068).
 *
 * Defines wire signaling payloads, voice peer state, and client connection options.
 */

export type WebRTCConnectionState =
  | 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'failed' | 'closed';

export const WebRTCConnectionStates = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting',
  FAILED: 'failed',
  CLOSED: 'closed',
} as const;

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
  autoReconnect?: boolean;
  reconnectIntervalMs?: number;
  onPeerJoined?: (peer: VoicePeer) => void;
  onPeerLeft?: (peerId: string, reason?: string) => void;
  onPeerMuted?: (peerId: string, isMuted: boolean) => void;
  onAudioLevel?: (level: number, isSpeaking: boolean) => void;
  onKicked?: (reason: string) => void;
  onError?: (error: Error | string) => void;
  onConnectionStateChange?: (state: WebRTCConnectionState) => void;
}

export interface PeerMeshOptions {
  iceServers?: RTCIceServer[];
  onSignal?: (message: SignalingMessage) => void;
  onRemoteStream?: (peerId: string, stream: MediaStream) => void;
}
