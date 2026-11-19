"""CORS policy for the gateway. Origins must be listed explicitly; a wildcard is refused."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def install_cors(app: FastAPI, cors_origins: str) -> None:
    """Allow the comma-separated origins in `cors_origins`, with credentials."""
    origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
    if "*" in origins:
        raise RuntimeError("RUNEFOBLE_CORS_ORIGINS must list explicit origins. '*' is refused.")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
