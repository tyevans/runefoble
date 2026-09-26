"""Bootstrap and apply Zanzibar authorization schema to SpiceDB."""

import argparse
import asyncio
import logging
import os
from pathlib import Path

from runefoble_auth.spicedb import SpiceDBClient

logger = logging.getLogger(__name__)

DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "schema" / "runefoble.zed"


async def bootstrap_schema(
    endpoint: str = "localhost:50051",
    token: str = "secret",
    schema_path: str | Path | None = None,
    client: SpiceDBClient | None = None,
    insecure: bool = True,
) -> str:
    """Read Zanzibar schema definition from disk and apply it to SpiceDB.

    Returns the applied schema text.
    """
    path = Path(schema_path) if schema_path else DEFAULT_SCHEMA_PATH
    if not path.is_file():
        # Fallback check for packaged location or root workspace location
        candidate = Path("libs/runefoble_auth/schema/runefoble.zed")
        if candidate.is_file():
            path = candidate
        else:
            raise FileNotFoundError(f"Zanzibar schema file not found at {path}")

    schema_text = path.read_text(encoding="utf-8")
    if not schema_text.strip():
        raise ValueError(f"Zanzibar schema at {path} is empty")

    spicedb = client or SpiceDBClient(
        endpoint=endpoint,
        token=token,
        insecure=insecure,
        use_mock=False,
    )
    await spicedb.write_schema(schema_text)
    logger.info("Successfully applied Zanzibar schema to SpiceDB at %s from %s", endpoint, path)
    return schema_text


def main() -> None:
    """CLI entrypoint for executing schema migrations."""
    parser = argparse.ArgumentParser(description="Apply Zanzibar schema to SpiceDB")
    parser.add_argument(
        "--endpoint",
        default=os.getenv("SPICEDB_ENDPOINT", "localhost:50051"),
        help="SpiceDB gRPC endpoint (default: localhost:50051 or SPICEDB_ENDPOINT)",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("SPICEDB_PRESHARED_KEY", os.getenv("SPICEDB_TOKEN", "secret")),
        help="SpiceDB preshared authentication key (default: SPICEDB_PRESHARED_KEY or 'secret')",
    )
    parser.add_argument(
        "--schema",
        default=None,
        help="Path to runefoble.zed schema file (default: libs/runefoble_auth/schema/runefoble.zed)",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        default=True,
        help="Connect using insecure plaintext gRPC (default: True)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    asyncio.run(
        bootstrap_schema(
            endpoint=args.endpoint,
            token=args.token,
            schema_path=args.schema,
            insecure=args.insecure,
        )
    )


if __name__ == "__main__":
    main()
