"""Production text-to-speech adapter for the espeak-ng command-line engine."""

from __future__ import annotations

import asyncio
from typing import ClassVar

from runefoble_platform.engine_ports import EngineUnavailableError
from voice_agent.synthesizer import AudioClip, BaseSynthesizer
from voice_agent.wav import decode_wav

DEFAULT_TIMEOUT_S = 30.0
SPEECH_SYNTHESIS_UNAVAILABLE = "speech_synthesis_unavailable"


class EspeakNgSynthesizer(BaseSynthesizer):
    """Runs `espeak-ng --stdout` and returns the WAV it writes.

    The text is sent on stdin, so no caller text reaches the command line.
    Any failure to start, exit, or return audio raises EngineUnavailableError.
    """

    engine_name: ClassVar[str] = "espeak-ng"

    def __init__(self, binary: str = "espeak-ng", timeout_s: float = DEFAULT_TIMEOUT_S):
        self.binary = binary
        self.timeout_s = timeout_s

    def _unavailable(self, message: str) -> EngineUnavailableError:
        return EngineUnavailableError(SPEECH_SYNTHESIS_UNAVAILABLE, self.engine_name, message)

    async def check_ready(self) -> None:
        """Run `espeak-ng --version`. A missing or failing binary is not ready."""
        returncode, _stdout, stderr = await self._run([self.binary, "--version"], b"")
        if returncode != 0:
            raise self._unavailable(
                f"'{self.binary}' --version exited with status {returncode}: {stderr}"
            )

    async def synthesize(self, text: str, voice: str) -> AudioClip:
        argv = [self.binary, "--stdout", "-v", voice, "--stdin"]
        returncode, stdout, stderr = await self._run(argv, text.encode("utf-8"))
        if returncode != 0:
            raise self._unavailable(f"'{self.binary}' exited with status {returncode}: {stderr}")

        try:
            clip = decode_wav(stdout)
        except ValueError as exc:
            raise self._unavailable(f"'{self.binary}' returned no usable audio: {exc}") from exc
        if clip.sample_count == 0:
            raise self._unavailable(f"'{self.binary}' returned zero audio samples")
        return clip

    async def _run(self, argv: list[str], stdin: bytes) -> tuple[int, bytes, str]:
        """Run the binary with a timeout. Return (exit status, stdout, decoded stderr)."""
        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise self._unavailable(f"cannot start '{self.binary}': {exc}") from exc

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(stdin), self.timeout_s)
        except TimeoutError as exc:
            process.kill()
            await process.wait()
            raise self._unavailable(
                f"'{self.binary}' did not finish within {self.timeout_s} s"
            ) from exc

        assert process.returncode is not None
        return process.returncode, stdout, stderr.decode("utf-8", errors="replace").strip()
