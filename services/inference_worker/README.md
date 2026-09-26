# Runefoble Distributed AI Inference Worker

High-performance AI inference worker for Runefoble, engineered to run on dedicated GPU host hardware (such as an NVIDIA RTX 3090) or alongside the local development cluster.

## Architecture

The worker implements stateful reasoning pipelines using **LangGraph** and **LangChain**:
1. **Natural Speech-to-Intent Graph**: Converts conversational voice/text actions into structured game mechanics, dice checks, and spatial grid mutations.
2. **The Watcher DM Narration Graph**: Synthesizes real-time narrative exploration, sensory atmosphere, and DM guidance based on active combat/session events.
3. **Missing Player Stand-in AI Graph**: Autonomously takes tactical turns for absent players, preserving their personality traits while applying DM-inflicted penalties (e.g. `"drunk"`, `"foolishness"`).

## Interfaces

- **HTTP REST API**: Fast synchronous endpoints (`/inference/v1/intent`, `/inference/v1/dm-narration`, `/inference/v1/stand-in-action`) for direct service orchestration.
- **Redis Streams Event Listener**: Asynchronous consumer subscribing to `runefoble.inference.requests` and emitting domain events (`runefoble.inference.results`) compliant with CloudEvents.
- **Pluggable Model Backends**:
  - `openai_compatible`: Direct integration with `llama-swap` / `vLLM` / local OpenAI-compatible servers (default port `8080`).
  - `ollama`: Direct integration with local Ollama daemon (default port `11434`).
  - `mock`: Safe offline fallback for continuous integration, property testing, and environments without an active GPU.

## Remote Deployment on Dedicated GPU Node

```bash
# 1. Clone or pull repo on remote host (e.g. debian@192.168.1.14)
git clone git@github.com:tyevans/runefoble.git
cd runefoble

# 2. Configure environment
cp services/inference_worker/.env.worker.example .env.worker

# 3. Launch worker
uv run runefoble-inference-worker --config .env.worker
```
