"""Validation of a portrait URL that a client sets at character creation (TASK-0905).

A portrait is one of these:

- an `http` or `https` URL with a host,
- an image data URI (`data:image/png`, `jpeg`, `gif`, `webp` or `svg+xml`),
- an asset reference to the asset service: `/api/v1/assets/{uuid}` with an optional query.

The URL must not contain whitespace, quotes or angle brackets, because the portrait
composer writes it into an SVG attribute. Any other value returns 422.
"""

from __future__ import annotations

import re
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import AfterValidator

MAX_PORTRAIT_URL_LENGTH = 65_536

_FORBIDDEN = re.compile(r"[\s\"'<>`]")
_IMAGE_DATA_URI = re.compile(r"^data:image/(png|jpeg|gif|webp|svg\+xml)[;,]")
_ASSET_REFERENCE = re.compile(
    r"^/api/v1/assets/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}(\?[^#]*)?$"
)


def validate_portrait_url(value: str) -> str:
    """Return the value when it is an allowed portrait URL. Raise ValueError when it is not."""
    if not value or len(value) > MAX_PORTRAIT_URL_LENGTH:
        raise ValueError("portrait_url must hold 1 to 65536 characters")
    if _FORBIDDEN.search(value):
        raise ValueError("portrait_url must not contain whitespace, quotes or angle brackets")
    if _IMAGE_DATA_URI.match(value) or _ASSET_REFERENCE.match(value):
        return value
    parts = urlsplit(value)
    if parts.scheme in ("http", "https") and parts.netloc:
        return value
    raise ValueError(
        "portrait_url must be an http(s) URL, an image data URI or /api/v1/assets/{id}"
    )


PortraitUrl = Annotated[str, AfterValidator(validate_portrait_url)]
