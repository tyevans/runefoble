"""Parse a media asset upload body: multipart/form-data, JSON with base64, or raw bytes."""

from __future__ import annotations

import base64
from dataclasses import dataclass

from fastapi import HTTPException, Request


@dataclass(frozen=True)
class AssetUpload:
    """The bytes and the declared metadata of one upload."""

    data: bytes
    filename: str
    content_type: str
    bucket: str | None
    asset_type: str
    campaign_id: str | None


async def parse_asset_upload(request: Request) -> AssetUpload:
    """Read the upload from its wire format. A malformed payload returns 400."""
    ct_header = request.headers.get("content-type", "")
    if "application/json" in ct_header:
        return await _parse_json(request)
    if "multipart/form-data" in ct_header:
        return await _parse_multipart(request)
    return await _parse_raw(request, ct_header)


async def _parse_json(request: Request) -> AssetUpload:
    try:
        body = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Malformed JSON body: {exc}") from exc

    b64_str = body.get("data_base64", "")
    if not b64_str:
        raise HTTPException(status_code=400, detail="Missing required 'data_base64' field.")
    try:
        data = base64.b64decode(b64_str)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64 payload: {exc}") from exc

    return AssetUpload(
        data=data,
        filename=body.get("filename", "upload.bin"),
        content_type=body.get("content_type", ""),
        bucket=body.get("bucket"),
        asset_type=body.get("asset_type", "avatar"),
        campaign_id=body.get("campaign_id") or None,
    )


async def _parse_multipart(request: Request) -> AssetUpload:
    form = await request.form()
    upload_file = form.get("file")
    if not upload_file or not hasattr(upload_file, "read"):
        raise HTTPException(
            status_code=400, detail="Missing 'file' field in multipart/form-data payload."
        )
    return AssetUpload(
        data=await upload_file.read(),
        filename=getattr(upload_file, "filename", None) or "upload.bin",
        content_type=getattr(upload_file, "content_type", None)
        or str(form.get("content_type", "")),
        bucket=str(form.get("bucket")) if "bucket" in form else None,
        asset_type=str(form.get("asset_type", "avatar")),
        campaign_id=str(form.get("campaign_id")) if form.get("campaign_id") else None,
    )


async def _parse_raw(request: Request, ct_header: str) -> AssetUpload:
    query = request.query_params
    return AssetUpload(
        data=await request.body(),
        filename=query.get("filename", "upload.bin"),
        content_type=ct_header.split(";")[0].strip(),
        bucket=query.get("bucket"),
        asset_type=query.get("asset_type", "avatar"),
        campaign_id=query.get("campaign_id") or None,
    )
