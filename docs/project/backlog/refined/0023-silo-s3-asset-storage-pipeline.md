---
id: 0023
title: Silo S3 Media Asset Bucket Storage & Character Avatar / Map Upload Pipeline
status: Refined
created: 2026-09-25
dependencies: [TASK-0008, TASK-0009]
governing_adrs: [ADR-0001, ADR-0005, ADR-0011]
target_release: 0.1.0
---

# TASK-0023 — Silo S3 Media Asset Bucket Storage & Character Avatar / Map Upload Pipeline

## Summary
Implement a secure media asset storage service (`SiloStorageService`) in `libs/runefoble_platform/storage.py` and frontdoor asset endpoints in `gateway/api` allowing players and DMs to upload, store, and stream character avatars and tactical battlemaps. Integrates with the platform's MinIO-compatible Silo S3 service (`http://silo:9000`), generating signed URLs, verifying MIME types and size limits, and publishing `AssetUploaded` domain events.

## Governing Architecture & ADRs
- **ADR-0001**: Zanzibar authorization with SpiceDB (verifies `character:edit` or `campaign:edit_map` before allowing asset upload).
- **ADR-0005**: Kubernetes-first infrastructure with Silo S3 container.
- **ADR-0011**: Event Sourcing with `eventsource-py` (`AssetUploaded`, `AssetDeleted`).

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Domain Events (`libs/runefoble_events/src/runefoble_events/base.py` or new `asset.py`)**:
   - `AssetUploaded`: `asset_id`, `bucket`, `object_key`, `content_type`, `byte_size`, `owner_id`, `url`.
   - `AssetDeleted`: `asset_id`, `bucket`, `object_key`, `deleted_by`.
2. **Storage Platform Service (`libs/runefoble_platform/src/runefoble_platform/storage.py`)**:
   - `SiloStorageClient` supporting bucket provisioning, object put, object get, deletion, and presigned download/upload URL generation with mock/in-memory fallback when Silo daemon is remote.
3. **Gateway Frontdoor Endpoints (`gateway/api/src/gateway_api/assets.py` & router)**:
   - `POST /api/v1/assets/upload`: Multi-part or binary upload with asset metadata (`asset_type`: `avatar` | `battlemap` | `audio`), returning permanent CDN/Silo URL and asset metadata.
   - `GET /api/v1/assets/{asset_id}`: Retrieves asset metadata and public stream URL.
   - `DELETE /api/v1/assets/{asset_id}`: Deletes asset.
4. **Blackbox TDD Suite (`tests/test_blackbox_silo_assets.py`)**:
   - Frontdoor tests using `TestClient` verifying upload of avatar PNG/JPEG, content validation, metadata retrieval, event dispatching, and deletion.
5. **File Invariant Check**:
   - All touched files remain strictly under 500 lines.
