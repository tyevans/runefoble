/**
 * WebRTC Peer Connection Mesh Coordinator (TASK-0068).
 *
 * Coordinates RTCPeerConnection mesh topology, SDP offer/answer exchanges,
 * ICE candidate queueing, remote audio streams, and DOM audio elements.
 */

import type { SignalingMessage, PeerMeshOptions } from './webrtc-types.ts';

export class PeerConnectionMesh {
  private peerConnections = new Map<string, RTCPeerConnection>();
  private remoteStreams = new Map<string, MediaStream>();
  private audioElements = new Map<string, HTMLAudioElement>();
  private pendingCandidates = new Map<string, RTCIceCandidateInit[]>();
  private options: PeerMeshOptions;

  constructor(options: PeerMeshOptions = {}) { this.options = options; }

  public async createPeerConnection(
    remotePeerId: string, isInitiator: boolean, localStream?: MediaStream | null, localPeerId?: string
  ): Promise<RTCPeerConnection> {
    if (this.peerConnections.has(remotePeerId)) return this.peerConnections.get(remotePeerId)!;

    const pc = new RTCPeerConnection({ iceServers: this.options.iceServers });
    this.peerConnections.set(remotePeerId, pc);

    pc.onicecandidate = (e) => {
      if (e.candidate) this.options.onSignal?.({
        type: 'webrtc_ice_candidate', from_peer: localPeerId || '', to_peer: remotePeerId, candidate: e.candidate.toJSON(),
      });
    };

    pc.ontrack = (e) => {
      if (e.streams && e.streams[0]) {
        const stream = e.streams[0];
        this.remoteStreams.set(remotePeerId, stream);
        this.attachAudioElement(remotePeerId, stream);
        this.options.onRemoteStream?.(remotePeerId, stream);
      }
    };

    if (localStream) for (const track of localStream.getAudioTracks()) pc.addTrack(track, localStream);

    if (isInitiator) {
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      this.options.onSignal?.({ type: 'webrtc_offer', from_peer: localPeerId || '', to_peer: remotePeerId, sdp: offer });
    }

    return pc;
  }

  public async handleOffer(
    fromPeer: string, sdp: RTCSessionDescriptionInit, localStream?: MediaStream | null, localPeerId?: string
  ): Promise<RTCSessionDescriptionInit> {
    const pc = await this.createPeerConnection(fromPeer, false, localStream, localPeerId);
    await pc.setRemoteDescription(new RTCSessionDescription(sdp));
    await this.flushPendingCandidates(fromPeer, pc);
    const answer = await pc.createAnswer();
    await pc.setLocalDescription(answer);
    return answer;
  }

  public async handleAnswer(fromPeer: string, sdp: RTCSessionDescriptionInit): Promise<void> {
    const pc = this.peerConnections.get(fromPeer);
    if (pc) {
      await pc.setRemoteDescription(new RTCSessionDescription(sdp));
      await this.flushPendingCandidates(fromPeer, pc);
    }
  }

  public async handleIceCandidate(fromPeer: string, candidate: RTCIceCandidateInit): Promise<void> {
    const pc = this.peerConnections.get(fromPeer);
    if (pc && pc.remoteDescription) {
      await pc.addIceCandidate(new RTCIceCandidate(candidate));
    } else {
      const queue = this.pendingCandidates.get(fromPeer) || [];
      queue.push(candidate);
      this.pendingCandidates.set(fromPeer, queue);
    }
  }

  public async handleSignal(
    msg: SignalingMessage, localStream?: MediaStream | null, localPeerId?: string
  ): Promise<void> {
    if (msg.type === 'webrtc_offer' && msg.from_peer && msg.sdp) {
      const answer = await this.handleOffer(msg.from_peer, msg.sdp, localStream, localPeerId);
      this.options.onSignal?.({
        type: 'webrtc_answer', from_peer: localPeerId || '', to_peer: msg.from_peer, sdp: answer,
      });
    } else if (msg.type === 'webrtc_answer' && msg.from_peer && msg.sdp) {
      await this.handleAnswer(msg.from_peer, msg.sdp);
    } else if (msg.type === 'webrtc_ice_candidate' && msg.from_peer && msg.candidate) {
      await this.handleIceCandidate(msg.from_peer, msg.candidate);
    } else if (msg.type === 'webrtc_peer_left' && msg.peer_id) {
      this.closePeer(msg.peer_id);
    }
  }

  public addLocalTrack(track: MediaStreamTrack, stream: MediaStream): void {
    for (const pc of this.peerConnections.values()) pc.addTrack(track, stream);
  }
  public setPeerVolume(peerId: string, volume: number): void {
    const el = this.audioElements.get(peerId);
    if (el) el.volume = Math.max(0, Math.min(1, volume));
  }
  public setPeerMute(peerId: string, muted: boolean): void {
    const el = this.audioElements.get(peerId);
    if (el) el.muted = muted;
  }

  public closePeer(peerId: string): void {
    const pc = this.peerConnections.get(peerId);
    if (pc) { pc.close(); this.peerConnections.delete(peerId); }
    this.remoteStreams.delete(peerId);
    this.pendingCandidates.delete(peerId);
    this.removeAudioElement(peerId);
  }

  public closeAll(): void {
    for (const pc of this.peerConnections.values()) pc.close();
    this.peerConnections.clear();
    this.remoteStreams.clear();
    this.pendingCandidates.clear();
    for (const el of this.audioElements.values()) { el.pause(); el.srcObject = null; el.remove(); }
    this.audioElements.clear();
  }

  public getPeerConnection(id: string): RTCPeerConnection | undefined { return this.peerConnections.get(id); }
  public getPeerConnections(): Map<string, RTCPeerConnection> { return this.peerConnections; }
  public getRemoteStream(id: string): MediaStream | undefined { return this.remoteStreams.get(id); }
  public getRemoteStreams(): Map<string, MediaStream> { return this.remoteStreams; }

  private async flushPendingCandidates(peerId: string, pc: RTCPeerConnection): Promise<void> {
    const pending = this.pendingCandidates.get(peerId);
    if (pending && pending.length > 0) {
      for (const cand of pending) await pc.addIceCandidate(new RTCIceCandidate(cand));
      this.pendingCandidates.delete(peerId);
    }
  }

  private attachAudioElement(peerId: string, stream: MediaStream): void {
    if (typeof document === 'undefined') return;
    let el = this.audioElements.get(peerId);
    if (!el) {
      el = Object.assign(document.createElement('audio'), { autoplay: true });
      el.dataset.peerId = peerId;
      document.body.appendChild(el);
      this.audioElements.set(peerId, el);
    }
    el.srcObject = stream;
  }

  private removeAudioElement(peerId: string): void {
    const el = this.audioElements.get(peerId);
    if (el) { el.pause(); el.srcObject = null; el.remove(); this.audioElements.delete(peerId); }
  }
}
