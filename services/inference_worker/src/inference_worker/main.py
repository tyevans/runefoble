"""CLI entrypoint for Runefoble AI Inference Worker."""

import argparse
import logging
import sys

import uvicorn

from inference_worker.config import WorkerSettings


def parse_args():
    parser = argparse.ArgumentParser(description="Runefoble Distributed AI Inference Worker")
    parser.add_argument("--host", type=str, default=None, help="Host to bind on")
    parser.add_argument("--port", type=int, default=None, help="Port to listen on")
    parser.add_argument(
        "--backend", type=str, choices=["auto", "openai_compatible", "ollama", "mock"], default=None
    )
    parser.add_argument("--config", type=str, default=None, help="Path to .env configuration file")
    return parser.parse_args()


def main():
    args = parse_args()
    settings = WorkerSettings()

    host = args.host or settings.host
    port = args.port or settings.port
    log_level = settings.log_level.lower()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print(
        f"==> Starting Runefoble Inference Worker on {host}:{port} "
        f"(backend={args.backend or settings.backend})...",
        file=sys.stderr,
    )

    uvicorn.run(
        "inference_worker.api:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=False,
    )


if __name__ == "__main__":
    main()
