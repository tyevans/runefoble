# ADR-0008: Property-Based Testing with Hypothesis and Mutation Testing with Mutmut

## Context

Tabletop gaming engines involve complex combinatorial state spaces:
- Any dice notation format (`NdM+K`) can be rolled with boundary values.
- Tokens can move in any arbitrary sequence across non-uniform grid dimensions.
- Turn orders can be dynamically spliced when characters join mid-combat, drop unconscious, or take delayed turns.

Traditional example-based unit tests only check known "happy paths" and edge cases anticipated by the developer. Furthermore, high code coverage metrics often mask "weak assertions" where code is executed but correctness is not verified.

## Decision

We establish a two-tiered rigorous verification standard for all bounded contexts:

1. **Property-Based Testing with Hypothesis**:
   - Every domain aggregate must have generative property tests using `@given(...)`.
   - Invariants tested include:
     - *Grid Boundary Invariant*: No sequence of valid moves can place a token outside `[0, cols)` and `[0, rows)`.
     - *Dice Rolling Range Invariant*: Rolling `NdS+M` strictly yields `N * 1 + M <= total <= N * S + M`.
     - *Turn Rotation Cycle Invariant*: Advancing turns $K$ times through an initiative list of length $N$ advances rounds by exactly $\lfloor K / N \rfloor$.
     - *Hit Points Clamping Invariant*: Character current HP never exceeds max HP and never falls below 0.
2. **Mutation Testing with Mutmut**:
   - Mutation testing introduces deliberate artificial defects (mutants) into domain code (e.g. swapping `+` for `-`, reversing comparison operators, returning `None`).
   - Tests must actively fail to "kill" the mutant.
   - Core domain logic in `libs/` and `services/*/domain` must maintain a minimum **80% mutation kill score**.
3. **Continuous Enforcement**:
   - `make test-property` runs all Hypothesis property tests with 100 random examples per run.
   - `make test-mutation` runs Mutmut on core domain modules.

## Consequences

- Edge cases (such as off-by-one grid wrapping, negative dice modifiers, empty initiative lists) are caught automatically during local development.
- Test suites have genuine defect-detection power rather than vanity coverage percentages.
