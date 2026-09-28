---
id: '0304'
title: Rules Compendium SRD Monsters Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0048
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0008
governing_stories:
- US-0037
- US-0052
target_release: 0.8.0
---

# TASK-0304: Rules Compendium SRD Monsters Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/rules_compendium/src/rules_compendium/srd/monsters.py` (298 lines, 59.6% of limit) into modular submodules under `services/rules_compendium/src/rules_compendium/srd/monsters/` (`humanoids.py`, `giants_and_beasts.py`, `undead_and_dragons.py`, `__init__.py`), keeping each submodule strictly < 100 lines per Hard Invariant 6.

## Problem Statement
`services/rules_compendium/src/rules_compendium/srd/monsters.py` consolidates canonical SRD 5.1 monster statblocks into a single 298-line static definition file:
1. Humanoid skirmishers, spellcasters, and brutes (Goblins, Hobgoblins, Bugbears, Orcs, Bandits, Acolytes, Mages, Cultists).
2. Giants, beasts, and monstrosities (Ogres, Hill Giants, Wolves, Owlbears).
3. Undead and chromatic dragons (Skeletons, Zombies, Ghouls, Young Red Dragon).

As homebrew expansions, legendary actions, dynamic CR calculators, and spellcasting traits are added, this catalog will quickly breach the 500-line invariant limit unless structured into discrete category modules.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout within the `rules_compendium` service.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation of SRD compendium rule data.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 100 lines).

## Scope of Work
1. **Humanoids Submodule (`services/rules_compendium/src/rules_compendium/srd/monsters/humanoids.py`)**:
   - Extract humanoid statblocks (Goblin, Hobgoblin, Bugbear, Orc, Bandit, Acolyte, Mage, Cultist) (< 100 lines).
2. **Giants and Beasts Submodule (`services/rules_compendium/src/rules_compendium/srd/monsters/giants_and_beasts.py`)**:
   - Extract giant and beast statblocks (Ogre, Hill Giant, Wolf, Owlbear) (< 80 lines).
3. **Undead and Dragons Submodule (`services/rules_compendium/src/rules_compendium/srd/monsters/undead_and_dragons.py`)**:
   - Extract undead and dragon statblocks (Skeleton, Zombie, Ghoul, Young Red Dragon) (< 80 lines).
4. **Package Facade (`services/rules_compendium/src/rules_compendium/srd/monsters/__init__.py`)**:
   - Aggregate and export `CANONICAL_MONSTERS` list with 100% backwards compatibility (< 30 lines).
5. **Verification**:
   - Run `uv run pytest tests/test_blackbox_rules_compendium.py` to confirm zero regression in encounter builder or hybrid search.

## Definition of Done
- `services/rules_compendium/src/rules_compendium/srd/monsters.py` replaced by `services/rules_compendium/src/rules_compendium/srd/monsters/` package.
- All extracted submodules strictly < 100 lines each per Hard Invariant 6.
- 100% backwards compatibility preserved for `CANONICAL_MONSTERS` imports.
- All rules compendium tests pass cleanly.
