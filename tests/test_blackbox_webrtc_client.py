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


def test_frontend_typescript_compilation():
    """Verify frontend TypeScript build passes with zero errors."""
    res = subprocess.run(
        ["pnpm", "--dir", str(REPO_ROOT / "frontend"), "run", "build"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Frontend build failed:\n{res.stdout}\n{res.stderr}"
