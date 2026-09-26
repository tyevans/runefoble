# TASK-0006: Voice DSP Audio Conditioning and Slurred Speech Synthesis

## Status
Complete

## Summary
Implemented digital signal processing (DSP) transforms and phonetic slur engine in `services/voice_agent/src/voice_agent/dsp.py`. Integrated the `VoiceDSPPipeline` into the `/api/v1/voice/tts` and `/api/v1/voice/synthesize` endpoints to modulate pitch, apply sibilant slurring, insert inebriation hiccups, and compute audio filter coefficients for character afflictions (`drunk`, `whisper`, `underwater`, `ghostly`).

## Key Changes
- `services/voice_agent/src/voice_agent/dsp.py`:
  - Created `DSPFilterConfig` and `ProcessedSpeechResult` models.
  - Implemented `VoiceDSPPipeline` with phonetic transformations (`slur_phonemes`, `apply_text_transforms`) and audio parameter calculations (`compute_dsp_config`).
  - Kept file clean and concise (137 lines).
- `services/voice_agent/src/voice_agent/main.py`:
  - Added `filters: list[str]` to `TTSRequest`.
  - Exposed `/api/v1/voice/tts` endpoint alongside `/api/v1/voice/synthesize`.
  - Returned `conditioned_text`, `effects_applied`, and `dsp_parameters` in `TTSResponse`.
  - Kept file at 228 lines (<500 line limit).
- `tests/test_voice_agent_dsp.py`:
  - Added unit tests verifying slur generation, underwater/whisper acoustics, sub-50ms execution speed, and FastAPI HTTP response structures.

## Verification
- `uv run pytest`: 75/75 tests passed.
- `uv run ruff check .` & `uv run ruff format .`: Zero errors.
