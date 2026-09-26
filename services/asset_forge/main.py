"""Top-level entrypoint for asset-forge service."""

from asset_forge.main import app, main

__all__ = ["app", "main"]

if __name__ == "__main__":
    main()
