---
id: '0328'
title: Project Visualizer Markdown Renderer Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0217
- TASK-0291
governing_adrs:
- ADR-0004
- ADR-0013
governing_prds:
- PRD-0013
governing_stories:
- US-0043
target_release: 0.8.0
---

# TASK-0328: Project Visualizer Markdown Renderer Modular Decomposition

## Status
Proposed

## Summary
Decompose `tools/project_visualizer/static/js/markdown.js` (276 lines, 55.2% of limit) into modular sub-modules under `tools/project_visualizer/static/js/` (`markdown_inline.js`, `markdown_blocks.js`, and facade `markdown.js`), keeping all source files strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`tools/project_visualizer/static/js/markdown.js` encapsulates inline regex tokenizers, typography formatters (code, links, autolinks, bold, italic, strikethrough), block parsers (headers, blockquotes, tables, lists, alerts), and markdown rendering routines in a single monolithic script. As extended Markdown syntax, interactive artifact preview cards, and GFM alerts expand, this script risks breaching the 500-line invariant unless decomposed.

## Governing Architecture & ADRs
- **ADR-0004: Bauhaus Microfrontend Design System**: Design token inheritance and typography styling.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 120 lines).

## Scope of Work
1. **Inline Tokenizer & Formatter (`tools/project_visualizer/static/js/markdown_inline.js`)**:
   - Extract inline typography formatting (code spans, bold/italic, strikethrough, autolinks, markdown links) and HTML escaping (< 100 lines).
2. **Block Syntax Parser (`tools/project_visualizer/static/js/markdown_blocks.js`)**:
   - Extract block-level parsers (GFM alert callouts, tables, task lists, blockquotes, headers) (< 110 lines).
3. **Facade Aggregator (`tools/project_visualizer/static/js/markdown.js`)**:
   - Wire inline and block parsers together into `window.visualizer.renderMarkdown`, maintaining backward compatibility (< 70 lines).
4. **Verification**:
   - Verify visualizer rendering via existing blackbox test suites (`test_visualizer_graph.py`, `test_visualizer_client.py`).

## Definition of Done
- `markdown.js` decomposed into inline and block parser modules.
- All extracted files strictly < 120 lines each per Hard Invariant 6.
- Existing visualizer test suite passes with 100% success rate.
