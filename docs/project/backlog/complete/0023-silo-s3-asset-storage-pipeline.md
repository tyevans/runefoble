---
id: 0023
title: Silo S3 Media Asset Bucket Storage & Character Avatar / Map Upload Pipeline
status: Complete
created: 2026-09-25
completed: 2026-09-26
dependencies: [TASK-0008, TASK-0009]
governing_adrs: [ADR-0001, ADR-0005, ADR-0011]
target_release: 0.1.0
---

# TASK-0023: Silo S3 Media Asset Bucket Storage & Character Avatar / Map Upload Pipeline

## Status
Complete

## Summary
Implemented a media asset storage service (`SiloStorageService`) in `libs/runefoble_platform/storage.py` and frontdoor asset endpoints in `gateway/api` allowing players and DMs to upload, store, and stream character avatars, tactical battlemaps, and ambient audio tracks. Integrates with the platform's MinIO-compatible Silo S3 service (`http://silo:9000`), generating signed URLs, verifying MIME types and size limits, and publishing `AssetUploaded` and `AssetDeleted` domain events.

## Key Changes
- `libs/runefoble_events/src/runefoble_events/asset.py`:
  - Defined `AssetUploaded` domain event (`runefoble.events.asset.uploaded`) with `asset_id`, `bucket`, `object_key`, `content_type`, `byte_size`, `owner_id`, `url`.
  - Defined `AssetDeleted` domain event (`runefoble.events.asset.deleted`) with `asset_id`, `bucket`, `object_key`, `deleted_by`.
  - Registered with both full event type and short class name in `EventRegistry`.
- `libs/runefoble_events/src/runefoble_events/events.py` & `__init__.py`:
  - Re-exported `AssetUploaded` and `AssetDeleted`.
- `libs/runefoble_platform/src/runefoble_platform/storage.py`:
  - Implemented `SiloStorageService` with `upload_asset`, `get_asset`, `get_asset_by_id`, `get_asset_data_by_id`, `delete_asset`, `delete_asset_by_id`, and `generate_presigned_url`.
  - Added robust offline in-memory fallback mock when remote Silo instance is unavailable.
  - Added strict MIME validation (`image/png`, `image/jpeg`, `image/webp`, `image/svg+xml`, `audio/wav`, `audio/mpeg`) and 10MB maximum file size limit.
- `libs/runefoble_platform/src/runefoble_platform/__init__.py`:
  - Re-exported `SiloStorageService`, `get_storage_service`, `set_storage_service`, `AssetStorageError`, `AssetValidationError`, `AssetNotFoundError`, `ALLOWED_MIME_TYPES`, `MAX_ASSET_SIZE_BYTES`.
- `gateway/api/src/gateway_api/assets.py`:
  - Implemented `POST /api/v1/assets/upload` supporting both multipart/form-data and JSON base64 payloads, validating payloads and dispatching `AssetUploaded`.
  - Implemented `GET /api/v1/assets/{asset_id}` supporting metadata queries and raw binary streaming (`?stream=true` or `/stream`, `/download`).
  - Implemented `DELETE /api/v1/assets/{asset_id}` removing asset and dispatching `AssetDeleted`.
- `gateway/api/src/gateway_api/main.py`:
  - Included asset router at `/api/v1/assets`.
- `tests/test_blackbox_silo_assets.py`:
  - Hard Invariant 7 compliant blackbox test suite validating upload via multipart and JSON base64, metadata retrieval, binary streaming, download headers, invalid MIME rejection, payload size limit enforcement, deletion lifecycle (subsequent 404s), and Redis stream / in-memory event dispatching.

## Verification
- `uv run pytest tests/test_blackbox_silo_assets.py`: 11 passed.
- `uv run pytest`: 177 passed across entire monorepo.
- `uv run ruff check .`: Clean (all checks passed).
- File length limits: All touched and created files are strictly under 500 lines.
