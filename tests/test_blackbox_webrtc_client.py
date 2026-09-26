"""Blackbox tests for WebRTC client voice service and peer mesh modular decomposition (TASK-0068).

Governing ADRs: ADR-0002, ADR-0004, ADR-0009, ADR-0013.
Verifies:
  - Modular decomposition into webrtc-types.ts, webrtc-peer-mesh.ts, and webrtc-voice.ts.
  - Strict compliance with Hard Invariant 6 (< 500 lines per file) and task limits (< 200 lines each).
  - Backward compatibility of re-exports and public service contracts.
  - Interface contracts for PeerConnectionMesh and WebRTCVoiceService.
"""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVICES_DIR = REPO_ROOT / "frontend" / "src" / "services"


def test_webrtc_client_files_exist():
    """Verify all decomposed TypeScript files exist in frontend/src/services."""
    types_file = SERVICES_DIR / "webrtc-types.ts"
    mesh_file = SERVICES_DIR / "webrtc-peer-mesh.ts"
    voice_file = SERVICES_DIR / "webrtc-voice.ts"

    assert types_file.is_file(), "webrtc-types.ts must exist"
    assert mesh_file.is_file(), "webrtc-peer-mesh.ts must exist"
    assert voice_file.is_file(), "webrtc-voice.ts must exist"


def test_webrtc_client_file_line_limits():
    """Verify all decomposed files strictly adhere to line count limits and Hard Invariant 6."""
    limits = {
        "webrtc-types.ts": 70,
        "webrtc-peer-mesh.ts": 160,
        "webrtc-voice.ts": 150,
    }

    for filename, max_lines in limits.items():
        file_path = SERVICES_DIR / filename
        assert file_path.is_file()
        line_count = len(file_path.read_text(encoding="utf-8").splitlines())

        # Check task target limit
        assert line_count < max_lines, (
            f"{filename} has {line_count} lines, exceeding task target limit of {max_lines}"
        )
        # Check strict 200-line requirement from Definition of Done
        assert line_count < 200, (
            f"{filename} has {line_count} lines, exceeding strict DoD limit of 200"
        )
        # Check Hard Invariant 6 (< 500 lines)
        assert line_count < 500, (
            f"{filename} has {line_count} lines, exceeding Hard Invariant 6 limit of 500"
        )


def test_webrtc_types_contract():
    """Verify webrtc-types.ts defines necessary wire protocol and peer state types."""
    types_content = (SERVICES_DIR / "webrtc-types.ts").read_text(encoding="utf-8")

    assert "export type WebRTCConnectionState" in types_content
    assert "export const WebRTCConnectionStates" in types_content
    assert "export interface VoicePeer" in types_content
    assert "export interface SignalingMessage" in types_content
    assert "export interface WebRTCVoiceOptions" in types_content
    assert "export interface PeerMeshOptions" in types_content


def test_webrtc_peer_mesh_contract():
    """Verify webrtc-peer-mesh.ts provides complete RTCPeerConnection and audio DOM management."""
    mesh_content = (SERVICES_DIR / "webrtc-peer-mesh.ts").read_text(encoding="utf-8")

    assert "export class PeerConnectionMesh" in mesh_content
    assert "createPeerConnection" in mesh_content
    assert "handleOffer" in mesh_content
    assert "handleAnswer" in mesh_content
    assert "handleIceCandidate" in mesh_content
    assert "handleSignal" in mesh_content
    assert "addLocalTrack" in mesh_content
    assert "setPeerVolume" in mesh_content
    assert "setPeerMute" in mesh_content
    assert "closePeer" in mesh_content
    assert "closeAll" in mesh_content
    assert "getPeerConnection" in mesh_content
    assert "getRemoteStream" in mesh_content
    assert "attachAudioElement" in mesh_content
    assert "removeAudioElement" in mesh_content


def test_webrtc_voice_facade_backward_compatibility():
    """Verify webrtc-voice.ts preserves backward-compatible exports and public service methods."""
    voice_content = (SERVICES_DIR / "webrtc-voice.ts").read_text(encoding="utf-8")

    # Backward compatible re-exports
    assert "export * from './webrtc-types.ts';" in voice_content
    assert "export * from './webrtc-peer-mesh.ts';" in voice_content
    assert "export class WebRTCVoiceService" in voice_content

    # Public facade methods
    assert "public async connect(" in voice_content
    assert "public async startMicrophone(" in voice_content
    assert "public applyDspFilters(" in voice_content
    assert "public setMute(" in voice_content
    assert "public getPeerId(" in voice_content
    assert "public getSessionId(" in voice_content
    assert "public getUserId(" in voice_content
    assert "public getConnectionState(" in voice_content
    assert "public getPeerMesh(" in voice_content
    assert "public disconnect(" in voice_content


def test_frontend_typescript_compilation():
    """Verify frontend TypeScript build passes with zero errors."""
    res = subprocess.run(
        ["pnpm", "--dir", str(REPO_ROOT / "frontend"), "run", "build"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Frontend build failed:\n{res.stdout}\n{res.stderr}"
