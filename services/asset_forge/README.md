# Runefoble Asset Forge Service

Procedural Battlemap & Token Asset Forge Microservice for Runefoble.

## Overview
Generates high-resolution tactical battlemaps and transparent circular token portraits directly from natural language prompts, calculates line-of-sight wall segments and hazard coordinates, uploads media assets to Silo S3 object storage, and dispatches domain events over Redis Streams.

## Ports & Endpoints
- Port: `8008`
- Health: `GET /healthz`
- OpenAPI: `GET /openapi.json`
- UI Manifest: `GET /ui/manifest`
- Procedural Battlemap: `POST /api/v1/forge/battlemap`
- Token Portrait: `POST /api/v1/forge/token`
