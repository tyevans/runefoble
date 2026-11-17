# ADR-0016: Specifications Are Code in docs/project

## Status
Accepted

## Context
Runefoble keeps personas, PRDs, user stories, ADRs, and backlog tasks as Markdown files with YAML frontmatter under `docs/project/`. Automated tools read these files. The spec-ops baseline calls this practice "spec as code" (spec-ops ADR-0001). Runefoble has no ADR that states the practice. The practice is described only in `docs/project/README.md`.

## Decision
1. Every product, planning, and architecture record lives in `docs/project/` as a versioned Markdown file in git.
2. Each record uses frontmatter that matches the spec-ops schema for its record type.
3. Registries (`product/REGISTRY.md`, `user_stories/REGISTRY.md`, `adrs/REGISTRY.md`) index the records. A record without a registry row is a defect.
4. The file `specops.toml` at the repository root configures the spec-ops tooling for this project.

## Consequences
- Tools and reviewers read the same source of truth.
- Changes to specifications go through the same review as code.
- Record formats must follow the schema. Schema drift is a defect.
