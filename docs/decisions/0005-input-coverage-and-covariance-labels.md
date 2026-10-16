# 0005 — Input coverage and covariance labels (Codex T-003 review B1, B2)

Date: 2026-10-16. Status: Proposed by Claude; pending Codex re-check and owner merge.
Review: Codex on PR #3 at `6fc6936`, recorded in PR #6 (`2aa78df`).
Changes: `src/trader/portfolio/targets.py`, `src/trader/numerics.py`, `src/trader/planner/plan.py`, new `tests/unit/test_input_coverage.py`, `docs/portfolio-spec.md` v1.3 (§2.1, §6.1).

## B1 — Missing eligible-asset metadata silently became zero weight — **Accepted**

**Issue.** `compute_targets` validated the entries that were present, then filtered out any eligible id lacking an asset class or σ. Codex's reproductions:
- eligible A with `asset_class = {}` → `weights = {}`, cash 1.0;
- A with a class but `sigma = {}` → A = 0, cash 1.0.

In the second case, a held instrument could then exit through the planner's `exit` reason. That is a **sale caused by missing data**, which the spec forbids.

**Decision.** Coverage is checked before any filtering. Every eligible id must have an asset class (`INVALID_ASSET_CLASS`), a σ (`INVALID_SIGMA`), a trend score and a momentum return (`INVALID_SIGNAL`). The covariance labels must equal the eligible set (`INVALID_COVARIANCE`). The `MIN_VOL` re-check is unchanged, but now runs only on fully specified ids.

## B2 — Duplicate covariance labels double-counted risk — **Accepted**

**Issue.** A 2×2 matrix labelled `['A', 'A']` passed validation. `portfolio_vol({'A': 0.25})` returned 0.0707 instead of 0.05, because the weight was placed twice.

**Decision.**
- `validate_covariance` rejects non-unique labels, and turns non-numeric entries into `INVALID_COVARIANCE` instead of raw conversion errors.
- `portfolio_vol` also rejects duplicate labels (defence in depth), since every volatility passes through it.
- The planner now validates the covariance it receives (new §6.1 check 9) and requires it to cover every instrument held or targeted.

## Spec change

v1.3 makes these rules explicit in §2.1 and adds §6.1 check 9. No strategy rule, parameter or fixture value changed. `test_params_frozen` and all 28 fixture cases pass unchanged.

## Evidence

- `tests/unit/test_input_coverage.py`: 15 regression tests independent of the fixture. They include Codex's three counterexamples, missing trend score or momentum, a covariance missing or adding an id, a non-numeric entry, and planner duplicate or missing labels, plus positive controls.
- Codex's three counterexamples now raise `INVALID_ASSET_CLASS`, `INVALID_SIGMA` and `INVALID_COVARIANCE`.
- 575 tests pass locally; CI on the PR head is authoritative.

## Process

PR #6 (Codex's review record) targets the T-003 branch and edits `docs/handoff.md`. This fix does not touch the handoff, to avoid a conflict. The owner can merge PR #6 into the branch, or close it after Codex re-reviews.
