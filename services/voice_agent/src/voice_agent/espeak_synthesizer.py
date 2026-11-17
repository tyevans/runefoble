"""Production text-to-speech adapter for the espeak-ng command-line engine."""

from __future__ import annotations

import asyncio
from typing import ClassVar

from voice_agent.synthesizer import AudioClip, BaseSynthesizer, SpeechSynthesisUnavailable
from voice_agent.wav import decode_wav

DEFAULT_TIMEOUT_S = 30.0


class EspeakNgSynthesizer(BaseSynthesizer):
    """Runs `espeak-ng --stdout` and returns the WAV it writes.

    The text is sent on stdin, so no caller text reaches the command line.
    Any failure to start, exit, or return audio raises SpeechSynthesisUnavailable.
    """

    engine_name: ClassVar[str] = "espeak-ng"

    def __init__(self, binary: str = "espeak-ng", timeout_s: float = DEFAULT_TIMEOUT_S):
        self.binary = binary
        self.timeout_s = timeout_s

    async def synthesize(self, text: str, voice: str) -> AudioClip:
        argv = [self.binary, "--stdout", "-v", voice, "--stdin"]
        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise SpeechSynthesisUnavailable(f"cannot start '{self.binary}': {exc}") from exc

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(text.encode("utf-8")), timeout=self.timeout_s
            )
        except TimeoutError as exc:
            process.kill()
            await process.wait()
            raise SpeechSynthesisUnavailable(
                f"'{self.binary}' did not finish within {self.timeout_s} s"
            ) from exc

        if process.returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()
            raise SpeechSynthesisUnavailable(
                f"'{self.binary}' exited with status {process.returncode}: {detail}"
            )

        try:
            clip = decode_wav(stdout)
        except ValueError as exc:
            raise SpeechSynthesisUnavailable(
                f"'{self.binary}' returned no usable audio: {exc}"
            ) from exc
        if clip.sample_count == 0:
            raise SpeechSynthesisUnavailable(f"'{self.binary}' returned zero audio samples")
        return clip
