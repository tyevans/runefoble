# Product Requirements Documentation

Product requirement records (PRDs) capture user needs, measurable definitions of success, and scope boundaries.
Following the project documentation standard:
- PRDs state **needs and checkable outcomes**, never internal code structures.
- Records move through four lifecycle directories: `idea/`, `shaped/`, `accepted/`, and `shipped/`.
- A record is considered shaped when it answers the six core questions: who it is for, what they cannot do today, checkable outcomes, non-goals, costs/scale factors, and governing constraints.

## PRD Pipeline & Decomposition Tooling

To manage and decompose PRDs into granular, single-pass vertical slices and ADR spikes:
```bash
# Audit PRD status, buffer levels, and oversized proposed tasks
./scripts/decompose-prds.sh audit

# Scaffold a new PRD document
./scripts/decompose-prds.sh create --title "<Title>" --persona "<Persona>" --bc "<BC>"

# Decompose an accepted PRD into spikes and vertical slices
./scripts/decompose-prds.sh decompose --prd PRD-XXXX

# Synchronize PRD, User Story, and Backlog registries
./scripts/decompose-prds.sh sync
```
See [`docs/how-to/decompose-prds-into-vertical-slices.md`](../../how-to/decompose-prds-into-vertical-slices.md) for detailed guidelines.

