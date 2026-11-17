# ADR-0019: Agent Constitution and Diataxis Documentation

## Status
Accepted

## Context
AI agents write much of the code and docs in this repository. Their rules are in AGENTS.md. The spec-ops baseline calls these rules the agent constitution (spec-ops ADR-0008). The baseline also requires documentation that follows the Diataxis framework. AGENTS.md already names Diataxis, but no ADR records the decision. Rules in AGENTS.md can drift from the code. The spec-ops tooling can check for drift.

## Decision
1. AGENTS.md is the agent constitution. It holds the Hard Invariants, the Definition of Ready, and the Definition of Done.
2. `docs/` follows the Diataxis framework: tutorials, how-to guides, reference, and explanation. No other categories are used.
3. A change to a Hard Invariant needs an ADR. The ADR must name the AGENTS.md section that changes.
4. Drift between AGENTS.md and the ADR set is checked with `spec-ops constitution` when the command is adopted (see the tooling decision in `docs/project/adrs/REGISTRY.md`).

## Consequences
- Agents read one rule source at the start of each task.
- Documentation changes follow the Diataxis type of the page.
